# TEST — Fase 0.3: Turno del agente en job asíncrono (queue_job, opcional)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Fase 0.3. Hasta ahora cada turno de chat retenía un
worker de Odoo hasta 2 min × 6 iteraciones. Este PR añade un modo asíncrono
**opcional y OFF por defecto** (el comportamiento síncrono actual no cambia):

- `requirements-oca.txt` + instalación del wheel `odoo-addon-queue-job` en la
  imagen (`Dockerfile.odoo`, `pip --no-deps`).
- Con `odoo_ai.async_enabled=1` **y** `queue_job` instalado: `chat()` y
  `execute_pending()` encolan el turno en un job y devuelven
  `{"type": "queued"}`; la UI hace **polling** (`poll_updates`) cada 1,5 s y
  pinta los mensajes a medida que el job los persiste.
- Si el parámetro está activo pero `queue_job` no está instalado/cargado, se
  degrada a síncrono sin error.

## Prerrequisitos

1. Reconstruir la imagen: `docker compose build odoo` (instala el wheel).
2. Para el modo asíncrono: en `docker-compose.yml`, usar el `command`
   alternativo comentado (instala `queue_job`, `--load=base,web,queue_job`,
   `--workers=2`) y poner `odoo_ai.async_enabled = 1` en Parámetros del sistema.

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test -i odoo_ai \
  --test-enable --stop-after-init
```

Nuevos en `test_async.py`: async desactivado por defecto (respuesta directa),
parámetro activo sin queue_job ⇒ sigue síncrono, `poll_updates` incremental
(mensajes nuevos y luego vacío) y `poll_updates` expone la confirmación
pendiente reconstruida.

## Prompts de prueba (chat)

**Modo síncrono (por defecto):** cualquier prompt del catálogo de la Fase 0.1
debe comportarse exactamente igual que antes.

**Modo asíncrono (activado según Prerrequisitos):**

| # | Acción | Comportamiento esperado |
|---|--------|--------------------------|
| 1 | «¿Qué oportunidades abiertas tenemos?» | El spinner «Pensando…» aparece al instante (la RPC vuelve enseguida); la respuesta llega por polling. En *Técnico → Queue Job* aparece el job `odoo_ai: turno de chat` en done |
| 2 | «Crea un lead para Acme» | Al terminar el job aparece la tarjeta Confirmar/Cancelar (reconstruida por polling) |
| 3 | Confirmar la tarjeta | Job `odoo_ai: confirmación`; el lead existe en CRM y la respuesta final llega por polling |
| 4 | Mandar un prompt y navegar a otra vista y volver | Sin errores JS en consola (el polling se detiene al desmontar el componente) |
| 5 | Dos usuarios a la vez con prompts lentos | Los workers no quedan bloqueados: la UI de ambos responde, los turnos corren como jobs |

## Casos negativos

- `odoo_ai.async_enabled=1` SIN el command alternativo (queue_job no cargado)
  → todo sigue funcionando en síncrono.
- Parar vLLM en modo asíncrono → el job termina, el polling cesa y aparece el
  mensaje de error amable del agente.
- ⚠️ Limitación conocida: si un job muere de forma anómala (kill -9, bug), la
  conversación puede quedar con `is_thinking=True` (spinner). Workaround:
  reintentar el job desde *Técnico → Queue Job* o crear conversación nueva.
  Pendiente de endurecer cuando el modo async se haga por defecto.

## Regresión

Catálogo completo de la Fase 0.1 en modo síncrono (default): sin cambios.
Verificar también el routing de la Fase 0.2 (logs `Router de packs`).
