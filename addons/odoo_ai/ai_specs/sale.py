from .common import _fn

PACK = "sale"
PACK_DESCRIPTION = "Ventas: crear presupuestos de venta para clientes."

SPECS = [
    {"is_write": True, "method": "_create_quotation", "schema": _fn(
        "create_quotation",
        "Crea un presupuesto de venta con una línea de producto.",
        {"customer_name": {"type": "string", "description": "Nombre del cliente."},
         "product_name": {"type": "string", "description": "Nombre del producto."},
         "quantity": {"type": "number", "description": "Cantidad (por defecto 1)."}},
        ["customer_name", "product_name"])},
]

DESCRIPTIONS = {
    "create_quotation": lambda a: (
        f"Crear un presupuesto para «{a.get('customer_name')}»: "
        f"{a.get('quantity', 1)} × «{a.get('product_name')}»."),
}
