# TEST — Fase 0.1: Tool packs por dominio (refactor)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

Refactor estructural ([ROADMAP.md](ROADMAP.md), Fase 0.1) — **sin cambio de
comportamiento esperado**:

- Specs movidos a `addons/odoo_ai/ai_specs/` (paquete **puro**, sin imports de
  Odoo, importable standalone — lo usará el harness de evals de la Fase 0.6),
  partidos por pack: `stock`, `crm`, `sale`, `account`, `purchase`.
- Cada spec lleva ahora la clave `pack`; cada pack declara `PACK_DESCRIPTION`
  (la usará el router de la Fase 0.2).
- Implementaciones movidas a mixins por dominio (`models/ai_tools_<pack>.py`)
  que heredan de `odoo.ai.tools`; `models/ai_tools.py` queda solo con el
  registro condicional y el despacho. Nuevo método `list_packs()`.
- Re-export de `TOOL_SPECS`/`DESCRIPTIONS` en `models.ai_tools` por
  compatibilidad.

## Prerrequisitos

Los mismos del stack base: `docker compose up --build` (+ LLM por perfil `gpu`
o endpoint externo). No hay módulos nuevos.

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test -i odoo_ai \
  --test-enable --stop-after-init
```

Esperado: `0 failed, 0 error(s)`. Novedades en `test_packs.py`:

- todo spec pertenece a un pack válido;
- **todo método de tool resuelve sobre `odoo.ai.tools`** (detecta mixins no
  importados en `models/__init__.py`);
- toda tool de escritura tiene descripción de confirmación;
- `list_packs()` devuelve los 5 packs con descripción;
- los imports históricos desde `models.ai_tools` siguen funcionando.

Verificación standalone (sin Odoo) de que los specs son puros:

```bash
python3 -c "import sys; sys.path.insert(0,'addons/odoo_ai'); import ai_specs; \
  print(len(ai_specs.TOOL_SPECS), 'tools en', ai_specs.PACK_NAMES)"
```

## Prompts de prueba (chat)

Al ser un refactor, la prueba es de **regresión completa**: todo el catálogo
siguiente debe comportarse exactamente igual que antes del cambio. Los ✍️
muestran tarjeta Confirmar/Cancelar.

### Inventario / Stock

| Prompt | Tool |
|---|---|
| «¿Cuánto stock hay del producto Mesa?» | `check_stock` |
| «¿Qué productos tienen menos de 5 unidades?» | `list_low_stock` |

### CRM — consulta

| Prompt | Tool |
|---|---|
| «Busca el cliente Acme» | `find_customer` |
| «¿Qué oportunidades abiertas tenemos?» | `list_open_opportunities` |
| «Enséñame el detalle de la oportunidad Web Acme» | `get_opportunity` |
| «¿Qué oportunidades llevan más de 14 días paradas?» | `list_stale_opportunities` |
| «¿Tenemos leads duplicados de joan@acme.com?» | `find_duplicate_opportunities` |

### CRM — acciones ✍️

| Prompt | Tool |
|---|---|
| «Crea un lead para Acme, contacto Joan Puig, email joan@acme.com» | `create_lead` |
| «Convierte el lead Lead Acme en oportunidad» | `convert_lead_to_opportunity` |
| «Mueve Web Acme a la etapa Propuesta» | `set_opportunity_stage` |
| «Marca Web Acme como ganada» | `mark_opportunity_won` |
| «Marca Web Bcorp como perdida, el precio era demasiado alto» | `mark_opportunity_lost` |
| «Asigna Web Acme a Maria» | `assign_opportunity` |
| «Prográmame una llamada para mañana con Web Acme: revisar presupuesto» | `schedule_activity` |
| «Apunta una nota en Web Acme: el cliente pide descuento» | `log_note` |
| «Pon Web Acme con ingreso esperado 5000 y prioridad alta» | `update_opportunity_fields` |

### Ventas / Facturación / Compras

| Prompt | Tool |
|---|---|
| ✍️ «Crea un presupuesto para Acme: 2 × Mesa» | `create_quotation` |
| «¿Qué facturas están pendientes de cobro?» | `list_unpaid_invoices` |
| «¿En qué estado está la factura INV/2025/00012?» | `invoice_status` |
| ✍️ «Registra el pago de la factura INV/2025/00012» | `register_invoice_payment` |
| «¿Qué pedidos de compra están abiertos?» | `list_open_purchase_orders` |
| ✍️ «Crea un pedido de compra a Proveedor SA: 50 × Tornillo M4» | `create_purchase_order` |
| ✍️ «Confirma el pedido de compra P00012» | `confirm_purchase_order` |

## Casos negativos

- «Mueve Web a Propuesta» (ambiguo) → pide precisión, no ejecuta.
- «¿Cuánto stock hay del producto Zzzzz?» → «no se encontró…», sin inventar.
- Usuario sin permisos de CRM → error de permisos en texto, sin traceback.
- «¿Cuántos leads se han creado este mes?» → sin tool: no debe inventar cifras.

## Regresión

Este PR ES la regresión: si cualquier prompt anterior cambia de comportamiento
respecto a la rama base (`claude/crm-automations`), es un bug del refactor.
