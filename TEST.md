# TEST — Fase 0.4: Auditoría de cambios del agente (OCA auditlog)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Fase 0.4. Traza independiente de «qué cambió el
agente» complementaria al historial de conversación:

- Wheel `odoo-addon-auditlog` añadido a `requirements-oca.txt` (imagen).
- `odoo.ai.audit.setup_rules()`: crea (idempotente) reglas de auditlog para
  los modelos que las tools de escritura tocan (`crm.lead`, `sale.order`,
  `purchase.order`, `account.move`, `account.payment`).
- Se ejecuta solo en el `post_init_hook` del addon; si auditlog se instala
  DESPUÉS, hay una acción de servidor «Configurar auditoría del Asistente IA».
- Sin auditlog instalado: no-op silencioso (nada cambia).

## Prerrequisitos

1. `docker compose build odoo` (instala el wheel).
2. Instalar `auditlog` en la BD: Apps → «Audit Log» → Instalar (o añadirlo al
   `-i` del command del compose).
3. Si `odoo_ai` ya estaba instalado: ejecutar la acción de servidor
   *Ajustes → Técnico → Acciones de servidor → Configurar auditoría del
   Asistente IA*.

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test -i odoo_ai \
  --test-enable --stop-after-init
# Con auditlog en la BD de test (cubre el camino completo):
docker compose run --rm odoo odoo -d odoo_test2 -i odoo_ai,auditlog \
  --test-enable --stop-after-init
```

`test_audit.py`: no-op sin auditlog, creación + idempotencia con auditlog,
y recordatorio de cobertura de `AUDITED_MODELS`.

## Prompts de prueba (chat)

Con auditlog instalado y reglas configuradas:

| # | Acción | Verificación |
|---|--------|--------------|
| 1 | «Crea un lead para Acme» + Confirmar | *Técnico → Audit → Logs*: entrada `create` sobre `crm.lead` con tu usuario |
| 2 | «Marca Web Acme como ganada» + Confirmar | Entrada `write` sobre `crm.lead` |
| 3 | «Registra el pago de la factura INV/…» + Confirmar | Entradas sobre `account.move` / `account.payment` |
| 4 | Cancelar una tarjeta de confirmación | **Ninguna** entrada nueva en el log |

Punto clave: el log de auditoría registra el **usuario real** (las tools corren
con sus permisos), no un usuario de sistema.

## Casos negativos

- Sin auditlog instalado: el addon instala/actualiza sin errores y el chat
  funciona igual (no-op).
- Ejecutar dos veces la acción de servidor → no duplica reglas.

## Regresión

Catálogo de la Fase 0.1 (síncrono) + routing 0.2 + async 0.3 si lo activaste.
