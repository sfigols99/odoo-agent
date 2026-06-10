# TEST — Ola 6: Finanzas (vencimientos core + remesas de pago OCA)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Ola 6. Catálogo total: 43 tools.

**Core account:**
- `list_upcoming_due_dates`: «¿qué vence esta semana?» — apuntes a cobrar y a
  pagar con vencimiento dentro de N días, marcando los ya vencidos.

**OCA `account_payment_order` (código 18.0 verificado):**
- `list_payment_orders`: remesas en borrador/confirmadas/con fichero.
- ✍️ `confirm_payment_order`: borrador → confirmada (`draft2open`); la
  generación del fichero bancario queda deliberadamente en la UI.

## Prerrequisitos

1. `docker compose build odoo`.
2. Apps: «Account Payment Order» (requiere configurar un *modo de pago*).
3. Datos: alguna factura validada con vencimiento próximo o pasado; para
   remesas, una orden de pago en borrador con líneas.

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test \
  -i odoo_ai,account_payment_order \
  --test-enable --test-tags /odoo_ai --stop-after-init
```

`test_account_oca.py`: vencimientos sin datos (texto, sin error), factura
vencida real (aparece con «VENCIDO» y «A COBRAR»), listado/confirmación de
remesas (incl. inexistente), tools ocultas sin módulo.

## Prompts de prueba (chat)

| # | Prompt | Tool | ¿Escritura? | Esperado |
|---|--------|------|-------------|----------|
| 1 | «¿Qué vence esta semana?» | `list_upcoming_due_dates` | No | Cobros y pagos ordenados por fecha, vencidos marcados ⚠️ |
| 2 | «¿Qué cobros tenemos atrasados?» | `list_upcoming_due_dates` | No | Los VENCIDOS aparecen primero |
| 3 | «¿Tenemos remesas de pago abiertas?» | `list_payment_orders` | No | Modo de pago, nº de líneas, total y estado |
| 4 | «Confirma la orden de pago PAY0001» | `confirm_payment_order` | Sí → tarjeta | Estado «Confirmada»; el fichero SEPA se genera desde la UI |

## Casos negativos

- Confirmar una orden ya confirmada → «no está en borrador».
- Confirmar una orden sin líneas → «no tiene líneas de pago», sin tocarla.
- Paso 4 sin el módulo → la tool no existe para el LLM.
- Usuario sin permisos de contabilidad → error de permisos en texto.

## Regresión

Catálogo previo completo (facturas/pagos igual que antes). Evals: 54 casos
(3 nuevos).
