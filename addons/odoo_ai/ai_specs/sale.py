from .common import _fn

PACK = "sale"
PACK_DESCRIPTION = ("Ventas: presupuestos de venta, tipos de pedido, "
                    "excepciones/bloqueos y aprobaciones de pedidos.")

SPECS = [
    {"is_write": True, "method": "_create_quotation", "schema": _fn(
        "create_quotation",
        "Crea un presupuesto de venta con una línea de producto.",
        {"customer_name": {"type": "string", "description": "Nombre del cliente."},
         "product_name": {"type": "string", "description": "Nombre del producto."},
         "quantity": {"type": "number", "description": "Cantidad (por defecto 1)."},
         "order_type": {"type": "string",
                        "description": "Tipo de pedido (opcional; requiere el "
                                       "módulo sale_order_type)."}},
        ["customer_name", "product_name"])},
    # ---------------- Extensiones OCA (Ola 3) ----------------
    # Verificadas contra el código 18.0 real de OCA/sale-workflow y
    # OCA/server-ux. Solo aparecen con su módulo instalado.
    {"is_write": False, "requires": ["sale_order_type"],
     "method": "_list_sale_order_types", "schema": _fn(
        "list_sale_order_types",
        "Lista los tipos de pedido de venta disponibles.",
        {})},
    {"is_write": False, "requires": ["sale_exception"],
     "method": "_list_order_exceptions", "schema": _fn(
        "list_order_exceptions",
        "Explica por qué un pedido de venta está bloqueado: lista sus "
        "excepciones (reglas incumplidas).",
        {"order_name": {"type": "string",
                        "description": "Número del pedido (p. ej. S00012)."}},
        ["order_name"])},
    {"is_write": False, "requires": ["sale_tier_validation"],
     "method": "_list_orders_to_approve", "schema": _fn(
        "list_orders_to_approve",
        "Lista los pedidos de venta pendientes de MI aprobación.",
        {})},
    {"is_write": True, "requires": ["sale_tier_validation"],
     "method": "_approve_sale_order", "schema": _fn(
        "approve_sale_order",
        "Aprueba (validación por niveles) un pedido de venta pendiente de mi visto bueno.",
        {"order_name": {"type": "string",
                        "description": "Número del pedido (p. ej. S00012)."}},
        ["order_name"])},
    {"is_write": True, "requires": ["sale_tier_validation"],
     "method": "_reject_sale_order", "schema": _fn(
        "reject_sale_order",
        "Rechaza (validación por niveles) un pedido de venta pendiente de mi aprobación.",
        {"order_name": {"type": "string",
                        "description": "Número del pedido (p. ej. S00012)."}},
        ["order_name"])},
]

DESCRIPTIONS = {
    "create_quotation": lambda a: (
        f"Crear un presupuesto para «{a.get('customer_name')}»: "
        f"{a.get('quantity', 1)} × «{a.get('product_name')}»"
        f"{(' (tipo: ' + a['order_type'] + ')') if a.get('order_type') else ''}."),
    "approve_sale_order": lambda a: (
        f"APROBAR el pedido de venta «{a.get('order_name')}» (validación por niveles)."),
    "reject_sale_order": lambda a: (
        f"RECHAZAR el pedido de venta «{a.get('order_name')}» (validación por niveles)."),
}
