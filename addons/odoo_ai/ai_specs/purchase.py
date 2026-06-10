from .common import _fn

PACK = "purchase"
PACK_DESCRIPTION = ("Compras: pedidos de compra/RFQ a proveedores, "
                    "solicitudes internas de compra y sus aprobaciones.")

SPECS = [
    {"is_write": False, "method": "_list_open_purchase_orders", "schema": _fn(
        "list_open_purchase_orders",
        "Lista los pedidos de compra que no están finalizados ni cancelados.",
        {})},
    {"is_write": True, "method": "_create_purchase_order", "schema": _fn(
        "create_purchase_order",
        "Crea un pedido de compra (RFQ) con una línea de producto.",
        {"vendor_name": {"type": "string", "description": "Nombre del proveedor."},
         "product_name": {"type": "string", "description": "Nombre del producto."},
         "quantity": {"type": "number", "description": "Cantidad (por defecto 1)."},
         "order_type": {"type": "string",
                        "description": "Tipo de pedido (opcional; requiere el "
                                       "módulo purchase_order_type)."}},
        ["vendor_name", "product_name"])},
    {"is_write": True, "method": "_confirm_purchase_order", "schema": _fn(
        "confirm_purchase_order",
        "Confirma un pedido de compra existente por su número.",
        {"po_name": {"type": "string", "description": "Número del pedido de compra (p. ej. P00012)."}},
        ["po_name"])},
    # ---------------- Extensiones OCA (Ola 5) ----------------
    # purchase_request verificado contra el código 18.0 real (estados
    # draft/to_approve/approved/rejected/done; button_to_approve/approved/rejected).
    {"is_write": True, "requires": ["purchase_request"],
     "method": "_create_purchase_request", "schema": _fn(
        "create_purchase_request",
        "Crea una solicitud interna de compra con un producto y la envía a "
        "aprobación.",
        {"product_name": {"type": "string", "description": "Producto solicitado."},
         "quantity": {"type": "number", "description": "Cantidad (por defecto 1)."},
         "reason": {"type": "string",
                    "description": "Motivo/descripción de la solicitud (opcional)."}},
        ["product_name"])},
    {"is_write": False, "requires": ["purchase_request"],
     "method": "_list_purchase_requests", "schema": _fn(
        "list_purchase_requests",
        "Lista las solicitudes internas de compra abiertas y su estado.",
        {})},
    {"is_write": True, "requires": ["purchase_request"],
     "method": "_approve_purchase_request", "schema": _fn(
        "approve_purchase_request",
        "Aprueba una solicitud interna de compra pendiente.",
        {"request_name": {"type": "string",
                          "description": "Referencia de la solicitud (p. ej. PR00007)."}},
        ["request_name"])},
]

DESCRIPTIONS = {
    "create_purchase_order": lambda a: (
        f"Crear un pedido de compra a «{a.get('vendor_name')}»: "
        f"{a.get('quantity', 1)} × «{a.get('product_name')}»"
        f"{(' (tipo: ' + a['order_type'] + ')') if a.get('order_type') else ''}."),
    "confirm_purchase_order": lambda a: (
        f"Confirmar el pedido de compra «{a.get('po_name')}»."),
    "create_purchase_request": lambda a: (
        f"Crear y enviar a aprobación una solicitud de compra: "
        f"{a.get('quantity', 1)} × «{a.get('product_name')}»"
        f"{(' — ' + a['reason']) if a.get('reason') else ''}."),
    "approve_purchase_request": lambda a: (
        f"APROBAR la solicitud de compra «{a.get('request_name')}»."),
}
