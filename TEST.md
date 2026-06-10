# TEST — Ola 4: Almacén (albaranes core + OCA stock)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Ola 4. Catálogo total: 37 tools.

**Core stock (sin OCA):**
- `list_pending_pickings`: albaranes en espera/confirmados/preparados.
- ✍️ `validate_picking`: valida una transferencia preparada; si Odoo pide una
  decisión (p. ej. backorder), lo explica y NO decide por su cuenta.

**OCA (verificado contra código 18.0 real):**
- `stock_available_unreserved`: `check_stock` añade «X sin reservar».
- `stock_inventory`: ✍️ `start_inventory_adjustment` (crea el ajuste agrupado
  y lo pone en progreso) + `list_inventory_adjustments`.

## Prerrequisitos

1. `docker compose build odoo`.
2. Apps: instalar «Stock Available Unreserved» y «Stock Inventory Adjustment».
3. Datos: producto almacenable con stock y algún albarán pendiente (crea un
   pedido de venta confirmado o una transferencia interna).

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test \
  -i odoo_ai,stock_available_unreserved,stock_inventory \
  --test-enable --test-tags /odoo_ai --stop-after-init
```

`test_stock_oca.py`: listado de pendientes, albarán inexistente, **flujo real
de validación** (quant → transferencia interna → confirmar → asignar →
validar), «sin reservar» con el módulo, flujo de ajuste de inventario, tools
ocultas sin módulo. La CI ejecuta esta combinación.

## Prompts de prueba (chat)

| # | Prompt | Tool | ¿Escritura? | Esperado |
|---|--------|------|-------------|----------|
| 1 | «¿Qué albaranes tenemos pendientes?» | `list_pending_pickings` | No | Lista con tipo, partner, estado y fecha prevista |
| 2 | «Valida el albarán WH/INT/00005» | `validate_picking` | Sí → tarjeta | Albarán en done; stock movido |
| 3 | «Valida WH/OUT/00007» (con cantidades parciales) | `validate_picking` | Sí → tarjeta | Mensaje «requiere una decisión adicional (backorder)»; nada validado a medias |
| 4 | «¿Cuánto stock hay de Mesa?» (con unreserved) | `check_stock` | No | Incluye «… sin reservar» |
| 5 | «Inicia un ajuste de inventario para Mesa» | `start_inventory_adjustment` | Sí → tarjeta | Ajuste en «in progress» visible en Inventario → Ajustes |
| 6 | «¿Qué ajustes de inventario están abiertos?» | `list_inventory_adjustments` | No | Incluye el del paso 5 |

## Casos negativos

- Validar un albarán ya hecho → «ya está validado», sin tocar nada.
- Validar uno en borrador → «no está listo (estado: draft)».
- Paso 5 sin `stock_inventory` instalado → la tool no existe para el LLM.
- Producto inexistente en el paso 5 → «No se encontró el producto…».

## Regresión

Catálogo previo completo; `check_stock` SIN el módulo unreserved debe mostrar
exactamente el formato de siempre. Evals: 48 casos (4 nuevos).
