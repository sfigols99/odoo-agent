# TEST — Ola 5: Compras (solicitudes internas + tipos de pedido, OCA)

> Convención y flujo de depuración con Claude Dispatch: ver [TESTING.md](TESTING.md).

## Alcance

[ROADMAP.md](ROADMAP.md), Ola 5. Catálogo total: 40 tools.

| Módulo OCA | Qué añade |
|---|---|
| `purchase_request` | ✍️ `create_purchase_request` (crea + envía a aprobación), `list_purchase_requests`, ✍️ `approve_purchase_request` |
| `purchase_order_type` | `create_purchase_order` acepta `order_type` (guardado por campo) |

> Gate aplicado: `purchase_discount` **no tiene wheel 18.0** en PyPI →
> pospuesto (anotado en requirements-oca.txt).

El flujo «necesito X, que alguien lo apruebe» es ideal para chat: el empleado
lo pide en una frase y el responsable lo aprueba en otra.

## Prerrequisitos

1. `docker compose build odoo`.
2. Apps: «Purchase Request», «Purchase Order Type».
3. Usuarios: uno normal (solicita) y uno con grupo *Purchase Request Manager*
  (aprueba) para probar el flujo completo con permisos reales.

## Tests automáticos

```bash
docker compose run --rm odoo odoo -d odoo_test \
  -i odoo_ai,purchase_request,purchase_order_type \
  --test-enable --test-tags /odoo_ai --stop-after-init
```

`test_purchase_oca.py`: flujo completo (crear → to_approve → listar →
aprobar), aprobación en estado incorrecto, tipo sin módulo (mensaje claro, no
crea nada), tipo con módulo, tools ocultas. La CI ejecuta esta combinación.

## Prompts de prueba (chat)

| # | Prompt | Tool | ¿Escritura? | Esperado |
|---|--------|------|-------------|----------|
| 1 | «Necesito 10 tornillos M4 para el taller, pide que los compren» | `create_purchase_request` | Sí → tarjeta | Solicitud en «Por aprobar» visible en Compras → Solicitudes |
| 2 | «¿Qué solicitudes de compra hay abiertas?» | `list_purchase_requests` | No | Incluye la del paso 1 con solicitante y líneas |
| 3 | (como manager) «Aprueba la solicitud PR00001» | `approve_purchase_request` | Sí → tarjeta | Estado «Aprobada» |
| 4 | «Crea un pedido de compra a Proveedor SA de tipo Importación: 50 tornillos» | `create_purchase_order` | Sí → tarjeta | RFQ con el tipo asignado |

## Casos negativos

- Paso 3 con el usuario normal (sin grupo manager) → error de permisos en
  texto; la solicitud NO cambia de estado.
- Aprobar una solicitud en borrador → «no está pendiente de aprobación».
- Paso 4 sin `purchase_order_type` → mensaje claro y NO se crea el pedido.
- Producto inexistente en el paso 1 → «No se encontró el producto…».

## Regresión

`create_purchase_order` SIN `order_type` idéntico a antes. Catálogo previo
completo. Evals: 51 casos (3 nuevos).
