# TEST — Ola 8: Contratos recurrentes + KPIs (OCA)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Ola 8 — **última ola del roadmap inicial**. Dos
packs nuevos (catálogo final: 55 tools, 9 packs):

**Pack `contract`** — OCA `contract` (alternativa gratuita a Suscripciones):
- `list_active_contracts` (próxima fecha de facturación), 
  `list_contracts_to_renew` (fin dentro de N días),
  ✍️ `generate_contract_invoice` (solo si el periodo ya venció; nunca factura
  por adelantado).

**Pack `kpi`** — OCA `mis_builder`:
- `list_kpi_reports`, `get_kpi_report` (calcula la matriz del informe y la
  resume por filas/periodos; el LLM la explica en lenguaje natural).

## Prerrequisitos

1. `docker compose build odoo`.
2. Apps: «Contracts» (OCA) y «MIS Builder».
3. Datos: un contrato con línea recurrente y fecha pasada (para generar
   factura) y un informe MIS configurado (p. ej. la plantilla de demo de
   mis_builder).

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test \
  -i odoo_ai,contract,mis_builder \
  --test-enable --test-tags /odoo_ai --stop-after-init
```

`test_contract_kpi.py`: listado de contratos, guard «sin líneas recurrentes»,
contratos a renovar (fecha pasada), tools KPI (listado + informe inexistente),
tools ocultas sin módulos.

## Prompts de prueba (chat)

| # | Prompt | Tool | ¿Escritura? | Esperado |
|---|--------|------|-------------|----------|
| 1 | «¿Qué contratos tenemos activos y cuándo se facturan?» | `list_active_contracts` | No | Contratos con próxima factura y fecha fin |
| 2 | «¿Qué contratos vencen el mes que viene?» | `list_contracts_to_renew` | No | Solo los que terminan en ≤30 días |
| 3 | «Genera la factura del contrato Mantenimiento Acme» | `generate_contract_invoice` | Sí → tarjeta | Factura creada SOLO si el periodo venció; el nº de factura aparece en la respuesta |
| 4 | «¿Qué informes de KPIs tenemos?» | `list_kpi_reports` | No | Nombres de los MIS configurados |
| 5 | «¿Cómo va el informe de ventas de este mes?» | `get_kpi_report` | No | Valores por KPI/periodo, explicados por el asistente |

## Casos negativos

- Paso 3 con el periodo aún no vencido → «aún no ha vencido… no se ha
  generado nada».
- Paso 3 con un contrato sin líneas recurrentes → mensaje claro.
- Informe KPI inexistente → lista los disponibles.
- Sin `contract`/`mis_builder` → tools invisibles para el LLM.

## Regresión

Catálogo completo de las 8 olas (55 tools). Con este tamaño, ejecuta también:

```bash
python evals/run_evals.py --verbose          # 66 casos
python evals/run_evals.py --packs crm        # comprueba el subset del router
```

y compara la accuracy global con tu línea base — es el indicador de si el
modelo actual (3B/7B) sigue eligiendo bien con el catálogo completo o hay que
bajar `router_threshold` / subir de modelo.
