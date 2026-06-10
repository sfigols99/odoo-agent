# odoo-agent — Asistente de IA embebido en Odoo 18

Asistente conversacional dentro de Odoo que opera sobre **stock, CRM/ventas,
facturación y compras**, usando un **modelo open-weights autoalojado** (vLLM en
GPU) y ejecutando las herramientas **en proceso** con los permisos del usuario.

> 📍 Plan de integración progresiva de módulos OCA: ver **[ROADMAP.md](ROADMAP.md)**.
> 🧪 Cómo probar y depurar (incl. Claude Dispatch y convención `TEST.md` por PR): ver **[TESTING.md](TESTING.md)**.

## Arquitectura

```
Navegador (UI OWL de chat)
        │  orm.call → odoo.ai.conversation.chat()
        ▼
Odoo 18  ── addon odoo_ai ──────────────────────────────┐
   • odoo.ai.agent: bucle de tool-calling               │
   • odoo.ai.tools: herramientas sobre el ORM (self.env)│
        │  POST /v1/chat/completions (tools)            │
        ▼                                               │
   vLLM (GPU)  Qwen2.5-7B-Instruct, OpenAI-compatible    │
                                                         │
PostgreSQL 15 ◀──────────────────────────────────────────┘

(Opcional) Servidor MCP HTTP  → reutiliza Odoo desde clientes externos
```

El **asistente embebido** es el camino principal. El **servidor MCP** (`odoo_mcp/`)
es una capa secundaria y opcional para clientes externos (p. ej. Claude Desktop).

> **Modelos de seguridad distintos.** El asistente embebido ejecuta las tools
> **en proceso con los permisos del usuario** y exige **confirmación humana** para
> toda escritura. El servidor MCP, en cambio, se autentica con una **cuenta de
> servicio compartida de bajo privilegio** (API key, ver Fase 7) y **no** aplica
> ese paso de confirmación: el control de acceso de MCP recae enteramente en los
> permisos de ese usuario y en exponer el endpoint solo con autenticación.

## Componentes y archivos

| Componente | Archivos |
|---|---|
| Base de datos | `k8s/postgres.yml` |
| Odoo + imagen custom | `k8s/odoo.yml`, `Dockerfile.odoo`, `addons/odoo_ai/` |
| Modelo LLM | `k8s/vllm.yml` |
| Ingress/TLS | `k8s/ingress.yml` |
| Secretos (plantilla) | `k8s/secrets.example.yml` |
| Servidor MCP | `odoo_mcp/`, `k8s/mcp.yml` |

## Demo rápida con Docker Compose

Para probar en local sin Kubernetes (ni registry de imágenes) usa
`docker-compose.yml`. Construye las imágenes localmente desde los Dockerfile.

```bash
# Postgres + Odoo (el addon se instala solo en la BD `odoo`)
docker compose up --build
# → http://localhost:8069   (Asistente IA → Chat)

# + vLLM en GPU (necesita GPU NVIDIA + nvidia-container-toolkit)
docker compose --profile gpu up --build

# + servidor MCP externo (define antes ODOO_API_KEY de un usuario de bajo privilegio)
docker compose --profile mcp up --build
```

El servicio de vLLM se llama `vllm-service` y escucha en el puerto 80, así que la
URL por defecto del asistente (`http://vllm-service/v1`) funciona sin tocar nada.
Sin el perfil `gpu`, apunta `odoo_ai.vllm_url` (Ajustes → Técnico → Parámetros del
sistema) a cualquier endpoint OpenAI-compatible que tengas a mano.

> **GPU pequeña (≤8 GB) / RTX 50-series.** El perfil `gpu` del compose viene
> ajustado para una RTX 5060 (8 GB, Blackwell sm_120): usa la imagen
> `vllm/vllm-openai:latest` (las wheels antiguas no traen kernels sm_120) y sirve
> `Qwen2.5-3B-Instruct-AWQ` bajo el alias `Qwen/Qwen2.5-7B-Instruct`, porque el 7B
> en FP16 (~15 GB) no cabe. Con más VRAM, sube el modelo en `docker-compose.yml`.

Las pruebas del addon se ejecutan dentro del contenedor de Odoo:

```bash
docker compose run --rm odoo odoo -d odoo_test -i odoo_ai \
  --test-enable --stop-after-init
```

## Prerrequisitos del clúster

- Nodo con **GPU NVIDIA** + device plugin / GPU Operator
  (`kubectl get nodes -o json | grep nvidia.com/gpu`).
- `ingress-nginx` y `cert-manager` (para `k8s/ingress.yml`).
- Un **registry** de imágenes (o cargar imágenes en el nodo para clústeres locales).

## Despliegue (orden recomendado)

```bash
# 0) Secretos (rellena los CHANGE_ME_* primero)
cp k8s/secrets.example.yml k8s/secrets.yml   # secrets.yml está en .gitignore
kubectl apply -f k8s/secrets.yml

# 1) Base: Postgres + (Odoo se despliega tras construir su imagen)
kubectl apply -f k8s/postgres.yml

# 2) Imagen custom de Odoo con el addon y despliegue
docker build -f Dockerfile.odoo -t odoo-ai:18.0 .
#   (local kind)     kind load docker-image odoo-ai:18.0
#   (local minikube) minikube image load odoo-ai:18.0
#   (registry)       docker tag/push y ajusta la imagen en k8s/odoo.yml
kubectl apply -f k8s/odoo.yml

# 3) vLLM (GPU). La primera vez descarga el modelo (lento; ver startupProbe)
kubectl apply -f k8s/vllm.yml

# 4) Ingress + TLS (ajusta host y email del ClusterIssuer)
kubectl apply -f k8s/ingress.yml

# 5) (Opcional) Servidor MCP externo
docker build -t odoo-mcp:1.0 ./odoo_mcp
kubectl apply -f k8s/mcp.yml
```

Tras desplegar Odoo, **inicializa una base de datos llamada `odoo`** e instala el
módulo: Apps → buscar "Odoo AI Assistant" → Instalar (o arranca con `-i odoo_ai`).

### Crear el usuario de bajo privilegio para el MCP (Fase 7)

1. Ajustes → Usuarios → crear `ai_integration` con solo los grupos necesarios
   (p. ej. Inventario: lectura; CRM: usuario).
2. Con ese usuario: Preferencias → Seguridad de la cuenta → Nueva API key.
3. Pon la key en el secret `mcp-secret` (`odoo-api-key`).

## Configuración del asistente

Parámetros en *Ajustes → Técnico → Parámetros del sistema* (valores por defecto
en `addons/odoo_ai/data/ai_config_params.xml`):

| Clave | Por defecto |
|---|---|
| `odoo_ai.vllm_url` | `http://vllm-service/v1` |
| `odoo_ai.model` | `Qwen/Qwen2.5-7B-Instruct` |
| `odoo_ai.max_tool_iterations` | `6` |
| `odoo_ai.temperature` | `0.1` |
| `odoo_ai.request_timeout` | `120` |

## Verificación end-to-end

1. **vLLM responde con tool_calls**
   ```bash
   kubectl port-forward svc/vllm-service 8000:80
   curl -s localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
     "model": "Qwen/Qwen2.5-7B-Instruct",
     "messages": [{"role":"user","content":"¿Cuánto stock hay del producto Mesa?"}],
     "tools": [{"type":"function","function":{"name":"check_stock",
       "parameters":{"type":"object","properties":{"product_name":{"type":"string"}},"required":["product_name"]}}}],
     "tool_choice": "auto"
   }' | python -m json.tool
   ```
   Debe aparecer `tool_calls` con `check_stock`.
2. **Lectura en Odoo:** abre *Asistente IA → Chat* y pregunta *"¿cuánto stock hay de
   \<producto real\>?"* → debe consultar y responder con datos reales.
3. **Escritura con confirmación:** *"crea un lead para Acme, email a@acme.com"* →
   aparece la tarjeta **Confirmar/Cancelar**; al confirmar, verifica el `crm.lead`
   en CRM. Repite con presupuesto/compra/pago.
4. **Seguridad por usuario:** repite con un usuario de permisos limitados → no debe
   poder leer/escribir lo que su perfil no permite (la tool devuelve el error).
5. **MCP externo:** apunta el *MCP inspector* o Claude Desktop a `http://<host>/mcp`
   y ejecuta `consultar_estoc_producte`.
6. **Producción:** `kubectl get pods` (probes OK), TLS válido en el Ingress, ningún
   secreto en texto plano, métricas de vLLM en `/metrics`.

## Notas / pendientes

- **Streaming (Fase 6, opcional):** la UI es single-shot; para streaming token a
  token usar `stream:true` en vLLM + `bus.bus._sendone` y `bus_service` en OWL.
- `create_purchase_order` / `register_invoice_payment` dependen de la config
  contable/almacén (diarios, UoM); ajusta si tu instancia difiere.
- Odoo a >1 réplica requiere filestore `ReadWriteMany` (el PVC actual es RWO).
- **Ocupación de workers:** cada turno de chat es síncrono y puede encadenar
  hasta `max_tool_iterations` llamadas al LLM (hasta `request_timeout` cada una)
  reteniendo un worker de Odoo. Con `workers = 2`, pocos usuarios concurrentes
  pueden saturarlos; sube `workers` o mueve el bucle a un job asíncrono para prod.
- Sin verificar en vivo: prueba el addon en una instancia Odoo 18 real antes de prod.
