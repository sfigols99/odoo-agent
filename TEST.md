# TEST — Ola 2: Extensiones OCA de CRM

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Ola 2 — primera ola de **módulos OCA** sobre el
registro condicional. Módulos verificados contra el código real 18.0 (wheels
en PyPI inspeccionados):

| Módulo OCA | Tools nuevas (solo aparecen con el módulo instalado) |
|---|---|
| `crm_lead_code` | `find_lead_by_code`; `get_opportunity` muestra el código |
| `crm_lead_product` | ✍️ `add_product_interest`, `list_product_interests` |
| `crm_phonecall` | ✍️ `log_phonecall`, `list_phonecalls` |
| `partner_identification` | `find_customer` muestra los documentos de identidad |

Los wheels van en la imagen (`requirements-oca.txt`), pero las tools solo se
activan al **instalar el módulo en la BD** (Apps). Sin módulos: nada cambia.

## Prerrequisitos

1. `docker compose build odoo` (instala los wheels nuevos).
2. Instalar en Apps los módulos que quieras probar: «Sequence Code for Leads /
   Opportunities», «Products in Leads», «CRM Phone Calls», «Partner
   Identification Numbers».
3. Datos: 1 oportunidad «Web Acme», 1 producto «Mesa».

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test \
  -i odoo_ai,crm_lead_code,crm_lead_product,crm_phonecall,partner_identification \
  --test-enable --test-tags /odoo_ai --stop-after-init
```

`test_crm_oca.py`: tools ocultas/bloqueadas sin módulo, búsqueda por código,
añadir/listar productos de interés, registrar/listar llamadas, código visible
en `get_opportunity`. La CI ejecuta esta combinación en cada push.

## Prompts de prueba (chat)

| # | Prompt | Tool | ¿Escritura? | Esperado |
|---|--------|------|-------------|----------|
| 1 | «Busca el lead con código LEAD/00001» | `find_lead_by_code` | No | Detalle con código incluido |
| 2 | «Enséñame la oportunidad Web Acme» | `get_opportunity` | No | El detalle incluye `código: LEAD/…` |
| 3 | «Añade interés en el producto Mesa a Web Acme, 3 unidades» | `add_product_interest` | Sí → tarjeta | Línea visible en la pestaña de productos del lead |
| 4 | «¿Qué productos le interesan a Web Acme?» | `list_product_interests` | No | «3 × Mesa …» |
| 5 | «Registra una llamada con Web Acme: hablamos del presupuesto, 15 min» | `log_phonecall` | Sí → tarjeta | Llamada en estado Held vinculada a la oportunidad |
| 6 | «¿Qué llamadas tengo hoy?» | `list_phonecalls` | No | Incluye la llamada del paso 5 |
| 7 | «Busca el cliente Acme» (con partner_identification y un NIF cargado) | `find_customer` | No | La línea incluye `IDs: NIF: …` |

## Casos negativos

- **Sin los módulos instalados** (aunque los wheels estén en la imagen): los
  prompts 1/3/5 NO deben disparar esas tools (no existen para el LLM); el
  asistente debe decir que no puede.
- Desinstalar `crm_lead_product` con líneas creadas → las tools desaparecen
  del catálogo en el siguiente turno (registro condicional en runtime).
- «Añade interés en el producto Zzzz a Web Acme» → «No se encontró el
  producto…».

## Regresión

- Catálogo completo de la Fase 0.1 (las 23 tools core, con y sin módulos OCA).
- `python evals/run_evals.py --verbose` — el banco incluye ya los 5 casos de
  esta ola; compara la accuracy con tu línea base de la Fase 0.6.
