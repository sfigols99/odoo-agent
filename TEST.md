# TEST — Ola 7: Helpdesk (OCA) + Proyectos (core condicional)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Ola 7. Dos packs NUEVOS (catálogo: 50 tools, 7 packs):

**Pack `helpdesk`** — OCA `helpdesk_mgmt` (alternativa gratuita al Helpdesk de
Enterprise; código 18.0 verificado):
- ✍️ `create_ticket`, `list_open_tickets` (con `only_mine`), `get_ticket`,
  ✍️ `assign_ticket`, ✍️ `close_ticket` (mueve a una etapa con `closed=True`).

**Pack `project`** — módulo **core** `project`, vía registro condicional (el
addon NO depende de él; demuestra que `requires` sirve también para core
opcional):
- ✍️ `create_task` (con asignado opcional), `list_my_tasks`.

## Prerrequisitos

1. `docker compose build odoo`.
2. Apps: «Helpdesk Management» (OCA) y «Proyecto» (core).
3. En Helpdesk, comprobar que existe alguna etapa marcada como *cerrada*.

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test \
  -i odoo_ai,helpdesk_mgmt,project \
  --test-enable --test-tags /odoo_ai --stop-after-init
```

`test_helpdesk_project.py`: ciclo completo del ticket (crear → listar →
detalle → asignar → cerrar), ticket ya cerrado, tarea con proyecto y asignado,
proyecto inexistente (lista disponibles), tools ocultas sin módulos.

## Prompts de prueba (chat)

| # | Prompt | Tool | ¿Escritura? | Esperado |
|---|--------|------|-------------|----------|
| 1 | «Abre un ticket: el cliente Acme no puede entrar al portal» | `create_ticket` | Sí → tarjeta | Ticket con número (HT…) en la primera etapa |
| 2 | «¿Qué tickets tenemos abiertos?» | `list_open_tickets` | No | Incluye el del paso 1 |
| 3 | «¿Cómo está el ticket HT00001?» | `get_ticket` | No | Detalle: contacto, etapa, asignado |
| 4 | «Asigna el ticket HT00001 a Maria» | `assign_ticket` | Sí → tarjeta | user_id cambiado |
| 5 | «Cierra el HT00001, ya está resuelto» | `close_ticket` | Sí → tarjeta | Etapa cerrada + nota en el chatter |
| 6 | «Crea una tarea en el proyecto Web: revisar el formulario de contacto» | `create_task` | Sí → tarjeta | Tarea visible en el tablero del proyecto |
| 7 | «¿Qué tareas tengo pendientes?» | `list_my_tasks` | No | Solo las tuyas, con vencimiento si lo hay |

## Casos negativos

- Cerrar un ticket ya cerrado → «ya está cerrado».
- Sin etapa de cierre configurada → mensaje que lo explica, sin mover nada.
- «Crea una tarea en el proyecto Inexistente…» → lista los proyectos
  disponibles.
- Sin `helpdesk_mgmt`/`project` instalados → las tools no existen para el LLM.

## Regresión

Catálogo previo completo. Con 50 tools, el **router de la Fase 0.2 es ya
imprescindible**: verifica en logs que `Router de packs` enruta a `helpdesk` /
`project` correctamente. Evals: 61 casos (7 nuevos).
