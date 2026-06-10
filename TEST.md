# TEST — Ola 3: Ventas (OCA sale-workflow + aprobaciones por niveles)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Ola 3. Módulos verificados contra el código 18.0
real (wheels de PyPI inspeccionados):

| Módulo OCA | Qué añade |
|---|---|
| `sale_order_type` | `list_sale_order_types`; `create_quotation` acepta `order_type` |
| `sale_exception` | `list_order_exceptions` («¿por qué está bloqueado S00012?») |
| `base_tier_validation` + `sale_tier_validation` | `list_orders_to_approve`, ✍️ `approve_sale_order`, ✍️ `reject_sale_order` |

Sinergia clave: la aprobación por niveles de OCA **encadena dos controles
humanos** — la tarjeta Confirmar/Cancelar del asistente + el tier de Odoo.
Catálogo total: 33 tools.

## Prerrequisitos

1. `docker compose build odoo`.
2. Instalar en Apps: «Sale Order Type», «Sale Exception», «Sale Tier Validation».
3. Para aprobaciones: crear una *Tier Definition* (Ajustes → Técnico →
   Definiciones de nivel) sobre `sale.order` con tu usuario como revisor, y un
   pedido con `request_validation` lanzado (botón «Solicitar validación»).

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test \
  -i odoo_ai,sale_order_type,sale_exception,sale_tier_validation \
  --test-enable --test-tags /odoo_ai --stop-after-init
```

`test_sale_oca.py`: presupuesto sin tipo sigue igual; con tipo sin módulo ⇒
mensaje claro y NO se crea pedido; con módulo ⇒ `type_id` asignado; flujo
completo de tier validation (definición → request → listar → aprobar);
tools ocultas sin módulos. La CI ejecuta esta combinación.

## Prompts de prueba (chat)

| # | Prompt | Tool | ¿Escritura? | Esperado |
|---|--------|------|-------------|----------|
| 1 | «¿Qué tipos de pedido de venta tenemos?» | `list_sale_order_types` | No | Lista de tipos |
| 2 | «Crea un presupuesto para Acme de tipo Exportación: 2 mesas» | `create_quotation` | Sí → tarjeta | Pedido con el tipo asignado (visible en el formulario) |
| 3 | «¿Por qué está bloqueado el pedido S00012?» | `list_order_exceptions` | No | Lista de excepciones con «(BLOQUEANTE)» si aplica |
| 4 | «¿Qué pedidos tengo pendientes de aprobar?» | `list_orders_to_approve` | No | Solo los pedidos donde TÚ eres revisor pendiente |
| 5 | «Aprueba el pedido S00012» | `approve_sale_order` | Sí → tarjeta | Review en estado approved; chatter del pedido lo refleja |
| 6 | «Rechaza el pedido S00031» | `reject_sale_order` | Sí → tarjeta | Review rejected |

## Casos negativos

- Prompt 2 **sin** `sale_order_type` instalado → «requiere el módulo OCA
  sale_order_type» y NO se crea el pedido.
- Prompt 5 sobre un pedido que NO espera tu aprobación → «no está pendiente de
  tu aprobación», sin tocar nada.
- Prompt 5 con un usuario que no es revisor → mismo mensaje (el `can_review`
  de OCA manda; el asistente no puede saltárselo).
- Tipo inexistente: «…de tipo Júpiter» → lista los tipos disponibles.

## Regresión

- Catálogo Fase 0.1 + Ola 2; `create_quotation` SIN `order_type` debe
  comportarse exactamente como antes.
- `python evals/run_evals.py --verbose` (44 casos; 6 nuevos de esta ola).
