# TEST — Ola 1: Automatizaciones de CRM + registro condicional (PR #2)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

- Registro condicional de tools (`requires=["modulo"]` en `TOOL_SPECS`).
- Pack CRM: consulta (`get_opportunity`), ciclo de vida
  (`convert_lead_to_opportunity`, `set_opportunity_stage`,
  `mark_opportunity_won`, `mark_opportunity_lost`), asignación/actividades
  (`assign_opportunity`, `schedule_activity`, `log_note`), enriquecimiento
  (`update_opportunity_fields`) e higiene (`list_stale_opportunities`,
  `find_duplicate_opportunities`).
- Punto del roadmap: **Ola 1** de [ROADMAP.md](ROADMAP.md).

## Prerrequisitos

- Stack arrancado: `docker compose up --build` (+ `--profile gpu` o un endpoint
  OpenAI-compatible en `odoo_ai.vllm_url`).
- Módulo `crm` instalado (ya es dependencia del addon).
- Datos de prueba: crea a mano en CRM al menos
  - 1 lead «Lead Acme» (tipo lead, contacto «Joan Puig», email `joan@acme.com`);
  - 2 oportunidades «Web Acme» y «Web Bcorp» en etapas distintas;
  - 1 usuario comercial adicional (p. ej. «Maria») y 1 usuario sin grupo de CRM.

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test -i odoo_ai \
  --test-enable --stop-after-init
```

Esperado: `0 failed, 0 error(s)`. Cubre registro condicional
(`test_tools_registry.py`), bucle del agente (`test_agent_loop.py`) y cada tool
de CRM sobre el ORM real (`test_crm_automations.py`).

## Prompts de prueba (chat)

| # | Prompt | Tool esperada | ¿Escritura? | Resultado esperado |
|---|--------|---------------|-------------|--------------------|
| 1 | «Enséñame el detalle de la oportunidad Web Acme» | `get_opportunity` | No | Etapa, comercial, importe, probabilidad y próxima actividad reales |
| 2 | «Convierte el lead Lead Acme en oportunidad» | `convert_lead_to_opportunity` | Sí → tarjeta | Tras confirmar, el lead pasa a tipo oportunidad en CRM |
| 3 | «Mueve Web Acme a la etapa Propuesta» | `set_opportunity_stage` | Sí → tarjeta | Etapa cambiada; si la etapa no existe, lista las disponibles |
| 4 | «Marca Web Acme como ganada» | `mark_opportunity_won` | Sí → tarjeta | Probabilidad 100% en CRM |
| 5 | «Marca Web Bcorp como perdida, el precio era demasiado alto» | `mark_opportunity_lost` | Sí → tarjeta | Oportunidad archivada con motivo de pérdida creado/enlazado |
| 6 | «Asigna Web Acme a Maria» | `assign_opportunity` | Sí → tarjeta | Comercial cambiado |
| 7 | «Prográmame una llamada para mañana con Web Acme: revisar presupuesto» | `schedule_activity` | Sí → tarjeta | Actividad tipo llamada con vencimiento mañana en la oportunidad |
| 8 | «Apunta una nota en Web Acme: el cliente pide descuento» | `log_note` | Sí → tarjeta | Nota visible en el chatter |
| 9 | «Pon Web Acme con ingreso esperado 5000, prioridad alta y etiqueta VIP» | `update_opportunity_fields` | Sí → tarjeta | Campos actualizados; etiqueta VIP creada si no existía |
| 10 | «¿Qué oportunidades llevan más de 14 días paradas?» | `list_stale_opportunities` | No | Lista (o «no hay») de abiertas sin actividad ni cambios recientes |
| 11 | «¿Tenemos leads duplicados de joan@acme.com?» | `find_duplicate_opportunities` | No | Lista de coincidencias por email/contacto |

> Repite 2-3 prompts en catalán (p. ej. «Marca Web Acme com a guanyada») — el
> asistente debe responder en el idioma del usuario.

## Casos negativos

- **Cancelar** la tarjeta del prompt 2 → el lead NO cambia de tipo y el chat
  continúa coherente.
- «Mueve Web a la etapa Propuesta» (nombre ambiguo, coincide con Acme y Bcorp)
  → mensaje «hay varias coincidencias…», sin ejecutar nada.
- Prompt 3 con una etapa inexistente («etapa Júpiter») → lista de etapas
  disponibles, sin traceback.
- Con el **usuario sin grupo CRM**: prompt 1 → error de permisos en texto
  legible, nunca un 500.
- Registro condicional: en `TOOL_SPECS` (entorno de prueba) cambia un
  `requires` a un módulo inexistente → la tool desaparece del chat y
  `execute_tool` la rechaza (cubierto también por test automático).

## Regresión

Deben seguir funcionando los packs previos:

- «¿Cuánto stock hay de \<producto real\>?» → `check_stock`.
- «Crea un lead para Acme, email a@acme.com» → `create_lead` + tarjeta.
- «Facturas pendientes de cobro» → `list_unpaid_invoices`.
- «Crea un pedido de compra a \<proveedor\>: 5 × \<producto\>» →
  `create_purchase_order` + tarjeta.
