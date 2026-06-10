from .common import _fn

PACK = "purchase"
PACK_DESCRIPTION = ("Compras: pedidos de compra/RFQ a proveedores, listar y "
                    "confirmar.")

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
         "quantity": {"type": "number", "description": "Cantidad (por defecto 1)."}},
        ["vendor_name", "product_name"])},
    {"is_write": True, "method": "_confirm_purchase_order", "schema": _fn(
        "confirm_purchase_order",
        "Confirma un pedido de compra existente por su número.",
        {"po_name": {"type": "string", "description": "Número del pedido de compra (p. ej. P00012)."}},
        ["po_name"])},
]

DESCRIPTIONS = {
    "create_purchase_order": lambda a: (
        f"Crear un pedido de compra a «{a.get('vendor_name')}»: "
        f"{a.get('quantity', 1)} × «{a.get('product_name')}»."),
    "confirm_purchase_order": lambda a: (
        f"Confirmar el pedido de compra «{a.get('po_name')}»."),
}
