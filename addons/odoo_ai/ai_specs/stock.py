from .common import _fn

PACK = "stock"
PACK_DESCRIPTION = "Inventario/almacén: stock disponible y productos bajo mínimos."

SPECS = [
    {"is_write": False, "method": "_check_stock", "schema": _fn(
        "check_stock",
        "Consulta el stock disponible de un producto por nombre.",
        {"product_name": {"type": "string",
                          "description": "Nombre o parte del nombre del producto."}},
        ["product_name"])},
    {"is_write": False, "method": "_list_low_stock", "schema": _fn(
        "list_low_stock",
        "Lista productos con stock a mano por debajo de un umbral.",
        {"threshold": {"type": "number",
                       "description": "Umbral de unidades (por defecto 5)."}})},
]

DESCRIPTIONS = {}
