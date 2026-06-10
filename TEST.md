# TEST — Fase 0.2: Selección dinámica de tools (router de packs)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Fase 0.2. Con modelos pequeños, exponer >20-25
schemas degrada la elección de tool. Este PR añade:

- Parámetro `odoo_ai.enabled_packs` («all» o csv, p. ej. «crm,sale»): limita
  qué packs ve el asistente, por instancia.
- **Router de dominio:** si las tools habilitadas superan
  `odoo_ai.router_threshold` (20 por defecto), una primera llamada barata SIN
  tools clasifica la intención del usuario en packs y solo se exponen esos.
  Fallbacks seguros: respuesta no reconocible o fallo del LLM ⇒ se exponen
  todos los packs habilitados (el agente nunca se queda mudo).
- `get_tool_schemas(packs=[...])` en `odoo.ai.tools`.

> Nota: con el catálogo actual (23 tools) y el umbral por defecto (20), el
> router está ACTIVO por defecto ⇒ cada turno hace 1 llamada LLM extra. Para
> desactivarlo, sube `odoo_ai.router_threshold` (p. ej. 999).

## Prerrequisitos

Stack base + un LLM (perfil `gpu` o endpoint externo). Parámetros en
*Ajustes → Técnico → Parámetros del sistema*.

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test -i odoo_ai \
  --test-enable --stop-after-init
```

Nuevos en `test_routing.py`: filtro por `enabled_packs`, fallback con config
inválida, sin llamada de router bajo el umbral, router subselecciona por
dominio (llamada SIN tools), fallback con respuesta basura y con error de LLM,
filtro `packs` de `get_tool_schemas`.

## Prompts de prueba (chat)

Con el umbral por defecto (router activo):

| # | Prompt | Comportamiento esperado |
|---|--------|--------------------------|
| 1 | «¿Cuánto stock hay del producto Mesa?» | En el log de odoo aparece `Router de packs: [...] -> ['stock']` y responde con datos de stock |
| 2 | «Marca Web Acme como ganada» | Router → `crm`; tarjeta de confirmación normal |
| 3 | «¿Qué facturas están pendientes de cobro?» | Router → `account`; lista facturas |
| 4 | «Hola, ¿qué sabes hacer?» | Sin dominio claro ⇒ router devuelve all/garbage ⇒ todos los packs; respuesta normal |
| 5 | (con `odoo_ai.enabled_packs = crm`) «¿Cuánto stock hay de Mesa?» | El pack stock NO está expuesto: el asistente dice que no puede consultarlo (no inventa cifras) |

Verifica el routing en vivo con: `docker compose logs -f odoo | grep "Router de packs"`.

## Casos negativos

- Apaga vLLM y pregunta algo → mensaje de error amable (el fallo del router no
  rompe el turno: primero cae el router a "todos" y después el turno principal
  devuelve el error controlado).
- `odoo_ai.enabled_packs = noexiste` → se comporta como `all` (fallback).
- `odoo_ai.router_threshold = 999` → ningún `Router de packs` en logs.

## Regresión

Catálogo completo del TEST.md de la Fase 0.1: mismas tools, mismas tarjetas de
confirmación. La única diferencia observable debe ser la línea de log del
router y (con packs restringidos) la indisponibilidad explícita del resto.
