# ROADMAP — Integración de módulos OCA en el Asistente IA

Objetivo: que el asistente pueda **automatizar progresivamente los módulos
gratuitos de la OCA** (todos son AGPL/LGPL), avanzando **módulo a módulo** en
"olas" pequeñas y verificables. Cada ola añade un *tool pack* que solo se activa
si su módulo está instalado (registro condicional, PR #2).

> Estado: documento vivo. Marca las casillas a medida que se completen olas.

---

## Estado actual

- [x] Addon `odoo_ai`: bucle de tool-calling en proceso, permisos del usuario,
      confirmación humana para escrituras, historial auditable.
- [x] Despliegue K8s + demo local con Docker Compose (perfiles `gpu` / `mcp`).
- [x] Suite de tests del registro y del bucle del agente (LLM mockeado).
- [ ] **PR #2 (en curso):** registro condicional (`requires=[...]`) + primer
      pack de CRM core (ciclo de vida, actividades, enriquecimiento, higiene).

## Principios (no negociables)

1. **Permisos del usuario.** Toda tool se ejecuta vía `self.env` con los ACL y
   record rules del usuario conectado. Nunca `sudo()` en tools.
2. **Confirmación humana para escrituras.** Toda tool `is_write` pasa por la
   tarjeta Confirmar/Cancelar. Sin excepciones, tampoco en packs nuevos.
3. **Registro condicional.** Cada tool declara `requires=["modulo"]`; solo se
   expone al LLM y se ejecuta si el módulo está instalado. El addon base sigue
   instalable sin ningún módulo OCA.
4. **Verificar antes de construir.** La OCA migra módulos por versiones; antes
   de cada ola se comprueba que el módulo tiene rama **18.0** (repo en GitHub /
   runboat / `pip index versions odoo-addon-<nombre>`). Si no está portado, se
   pospone o se contribuye la migración upstream.
5. **Texto, no excepciones.** Las tools devuelven siempre texto legible para el
   modelo (errores incluidos); nunca propagan excepciones al RPC.
6. **Solo Community + OCA (100% gratuito).** Ninguna integración puede depender
   de módulos de **Odoo Enterprise** (licencia de pago). Donde Enterprise cubre
   una función, se usa el equivalente gratuito de la OCA (ver tabla siguiente).

### OCA como sustituto gratuito de Enterprise

| Función (Enterprise, de pago) | Equivalente gratuito OCA usado aquí | Ola |
|---|---|---|
| Helpdesk | `helpdesk_mgmt` (OCA/helpdesk) | 7 |
| Informes contables avanzados | `account_financial_report` (OCA/account-financial-reporting) | 6 |
| Suscripciones | `contract` (OCA/contract) | 8 |
| Dashboards/consolidación KPI | `mis_builder` (OCA/mis-builder) | 8 |
| Aprobaciones | `base_tier_validation` (OCA/server-ux) | 3 |
| Colas/automatización en segundo plano | `queue_job` (OCA/queue) | Fase 0.3 |

El addon base ya cumple: sus `depends` (`crm`, `sale_management`, `account`,
`purchase`, `stock`, `product`, `web`, `base`) son todos de **Odoo Community**.

---

## Fase 0 — Plataforma para escalar (prerrequisito de las olas 3+)

El cuello de botella real no es escribir tools: es que **un modelo pequeño se
degrada con muchas tools** y que el bucle síncrono retiene workers. Estas piezas
preparan el terreno; las dos primeras son bloqueantes antes de superar ~25 tools.

| # | Pieza | Detalle | Módulo OCA implicado |
|---|---|---|---|
| 0.1 | **Tool packs por dominio** | Partir `ai_tools.py` en mixins por dominio (`ai_tools_crm.py`, `ai_tools_sale.py`, …) que se agregan al registro. Mismo modelo `odoo.ai.tools`, archivos separados. | — |
| 0.2 | **Selección dinámica de tools** | Con el modelo actual (3B AWQ en la 5060, 7B en cluster) exponer >20-25 schemas degrada la elección de tool. Opciones, en orden: (a) parámetro `odoo_ai.enabled_packs` por compañía; (b) *router* de dominio: primera llamada clasifica la intención (crm/ventas/stock/…) y la segunda solo recibe las tools de ese pack; (c) subset por retrieval sobre descripciones. Empezar por (a)+(b). | — |
| 0.3 | **Ejecución asíncrona** | Mover el bucle LLM a `queue_job` + notificar por `bus`: libera workers (hoy un turno puede retener un worker 2 min × 6 iteraciones) y habilita streaming real. | `queue_job` (OCA/queue) |
| 0.4 | **Auditoría reforzada** | Activar `auditlog` sobre los modelos que las tools escriben: traza independiente de "qué cambió el agente", complementaria al historial de conversación. | `auditlog` (OCA/server-tools) |
| 0.5 | **CI/compose con OCA** | La OCA publica wheels en PyPI (`odoo-addon-<nombre>`). Añadir `requirements-oca.txt` al `Dockerfile.odoo` y un job de CI que instala los packs y ejecuta `--test-enable` por pack. | — |
| 0.6 | **Evals de tool-calling** | Banco de ~30 prompts canónicos por pack (ES/CA) con la tool esperada; script que los lanza contra vLLM y mide aciertos. Sin esto no se puede saber si añadir un pack degrada los demás. | — |

## Proceso repetible por ola (checklist)

Para cada módulo/ola, siempre el mismo ciclo (1 rama + 1 PR por ola):

1. **Verificar** rama 18.0 del módulo OCA (GitHub/runboat/PyPI).
2. **Instalar** en el compose local (`requirements-oca.txt`) y probar a mano.
3. **Diseñar** las tools: qué lecturas, qué escrituras, qué pide confirmación;
   ojo a los flujos del módulo (wizards, estados) — la tool replica el flujo UI.
4. **Implementar** el pack con `requires=["modulo_oca"]` + descripciones de
   confirmación.
5. **Tests** `TransactionCase` por tool (con el módulo OCA como dependencia de
   test) + eval de tool-calling (0.6).
6. **Documentar** en README (tabla del pack) y marcar la casilla aquí.

---

## Olas de módulos

> Las tools marcadas ✍️ son de escritura (pasan por confirmación). Los nombres
> de módulo son los de las ramas 16/17 de la OCA; **confirmar el port a 18.0 en
> el paso 1 de cada ola**.

### Ola 1 — CRM core (en curso, PR #2)

- [x] Diseño e implementación del pack CRM core (sin OCA): ciclo de vida,
      asignación/actividades, enriquecimiento, higiene de pipeline.
- [ ] Merge + validación en vivo sobre Odoo 18.

### Ola 2 — CRM extensiones OCA (repo `OCA/crm`, `OCA/partner-contact`)

| Módulo | Aporta | Tools candidatas |
|---|---|---|
| `crm_lead_code` | Código secuencial por lead | buscar por código; incluir código en respuestas |
| `crm_lead_product` | Productos de interés en el lead | ✍️ añadir/quitar productos de interés; filtrar pipeline por producto |
| `crm_phonecall` | Registro de llamadas | ✍️ registrar llamada; listar llamadas pendientes del día |
| `crm_stage_probability` | Probabilidad fija por etapa | respetarla en `update_opportunity_fields` |
| `partner_identification` | Documentos de identidad del partner | completar `find_customer` con NIF/IDs |

### Ola 3 — Ventas (repo `OCA/sale-workflow`, `OCA/server-ux`)

| Módulo | Aporta | Tools candidatas |
|---|---|---|
| `sale_order_type` | Tipos de pedido con flujos propios | ✍️ crear presupuesto con tipo; listar por tipo |
| `sale_exception` | Reglas de bloqueo de pedidos | listar excepciones de un pedido; explicar por qué está bloqueado |
| `sale_automatic_workflow` | Confirmación/factura automática | ✍️ aplicar workflow a un pedido |
| `sale_quotation_number` | Numeración separada presupuesto/pedido | buscar por nº de presupuesto |
| `sale_order_revision` | Revisiones de presupuesto | ✍️ crear revisión; comparar revisiones |
| `base_tier_validation` (+`sale_tier_validation`) | Aprobaciones multinivel | listar pedidos pendientes de mi aprobación; ✍️ aprobar/rechazar — **sinergia directa con el gate de confirmación** |

### Ola 4 — Almacén (repos `OCA/stock-logistics-warehouse`, `OCA/stock-logistics-workflow`)

| Módulo | Aporta | Tools candidatas |
|---|---|---|
| `stock_inventory` | Ajustes de inventario agrupados | ✍️ iniciar/validar ajuste de un producto/ubicación |
| `stock_available_unreserved` | Stock disponible no reservado | enriquecer `check_stock` |
| `stock_demand_estimate` | Estimaciones de demanda | consultar demanda estimada; detectar roturas previstas |
| `stock_no_negative` | Bloqueo de stock negativo | explicar errores de validación al usuario |
| `stock_split_picking` | Partir albaranes | ✍️ partir albarán por líneas pendientes |
| `stock_cycle_count` | Conteos cíclicos | proponer/✍️ planificar conteos |

### Ola 5 — Compras (repo `OCA/purchase-workflow`)

| Módulo | Aporta | Tools candidatas |
|---|---|---|
| `purchase_request` | Solicitudes internas de compra | ✍️ crear solicitud; listar pendientes; ✍️ aprobar — flujo ideal para chat |
| `purchase_order_type` | Tipos de pedido de compra | ✍️ crear RFQ con tipo |
| `purchase_exception` | Reglas de bloqueo | explicar bloqueos |
| `purchase_discount` | Descuentos en líneas | ✍️ aplicar descuento (con confirmación) |

### Ola 6 — Facturación y finanzas (repos `OCA/account-payment`, `OCA/account-reconcile`, `OCA/account-financial-reporting`, `OCA/account-invoicing`)

| Módulo | Aporta | Tools candidatas |
|---|---|---|
| `account_due_list` | Lista de vencimientos | "¿qué vence esta semana?" |
| `account_payment_partner` / `account_payment_order` | Modos de pago y remesas SEPA | ✍️ añadir factura a remesa; listar remesas abiertas |
| `account_reconcile_oca` | Conciliación manual mejorada | proponer conciliaciones (lectura); ✍️ conciliar con confirmación |
| `account_financial_report` | Mayor, sumas y saldos, aged balance | consultas de informe resumidas por el LLM |
| `account_invoice_refund_link` | Vínculo factura-abono | trazar abonos de una factura |

### Ola 7 — Helpdesk y proyectos (repos `OCA/helpdesk`, `OCA/project`, `OCA/timesheet`)

| Módulo | Aporta | Tools candidatas |
|---|---|---|
| `helpdesk_mgmt` | Tickets de soporte | ✍️ crear/asignar/cerrar ticket; listar por SLA/equipo — caso de uso estrella para el agente |
| `helpdesk_mgmt_timesheet` | Partes de horas en tickets | ✍️ imputar tiempo |
| `project_task_code` | Código de tarea | buscar tarea por código |
| `project_template` | Plantillas de proyecto | ✍️ crear proyecto desde plantilla |
| `hr_timesheet_sheet` | Hojas de horas | resumen semanal; ✍️ enviar hoja |

### Ola 8 — Recurrencia y KPIs (repos `OCA/contract`, `OCA/mis-builder`)

| Módulo | Aporta | Tools candidatas |
|---|---|---|
| `contract` | Contratos con facturación recurrente | listar contratos por renovar; ✍️ crear contrato desde pedido; ✍️ generar factura del periodo |
| `mis_builder` | Informes KPI configurables | "¿cómo va el KPI X este mes?" — el agente lee la matriz del informe y la explica |

---

## Criterios de priorización (por qué este orden)

1. **Valor conversacional:** flujos donde "pedirlo en una frase" ahorra más
   clics (helpdesk, purchase_request, vencimientos) puntúan alto.
2. **Riesgo de escritura:** primero packs con escrituras reversibles (CRM,
   solicitudes); conciliación/remesas al final, cuando el patrón esté maduro.
3. **Madurez del port 18.0:** módulos con migración estable primero.
4. **Carga sobre el modelo:** cada ola añade 4-8 tools; a partir de la ola 3 es
   obligatorio tener la selección dinámica (0.2) en marcha.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Módulo OCA sin port 18.0 | Gate de verificación (paso 1); posponer o migrar upstream |
| Degradación del tool-calling al crecer el catálogo | Fase 0.2 (packs habilitables + router) y evals 0.6 como regresión |
| Modelo pequeño (3B AWQ en local) alucina argumentos | Confirmación humana ya cubre escrituras; evals por pack; subir de modelo cuando haya VRAM |
| Workers saturados con más usuarios | Fase 0.3 (`queue_job`) |
| Drift de APIs entre Odoo 16→18 en módulos OCA | Tests `TransactionCase` por tool con el módulo instalado en CI (0.5) |
