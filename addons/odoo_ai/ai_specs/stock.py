from .common import _fn

PACK = "stock"
PACK_DESCRIPTION = ("Inventario/almacén: stock disponible, productos bajo "
                    "mínimos, albaranes/transferencias y ajustes de inventario.")

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
    # ---------------- Albaranes / transferencias (Ola 4, core) ----------------
    {"is_write": False, "method": "_list_pending_pickings", "schema": _fn(
        "list_pending_pickings",
        "Lista los albaranes/transferencias pendientes (en espera, confirmados "
        "o preparados).",
        {})},
    {"is_write": True, "method": "_validate_picking", "schema": _fn(
        "validate_picking",
        "Valida un albarán/transferencia preparado por su número (p. ej. WH/OUT/00012).",
        {"picking_name": {"type": "string", "description": "Número del albarán."}},
        ["picking_name"])},
    # ---------------- Extensiones OCA (Ola 4) ----------------
    {"is_write": True, "requires": ["stock_inventory"],
     "method": "_start_inventory_adjustment", "schema": _fn(
        "start_inventory_adjustment",
        "Inicia un ajuste de inventario agrupado para un producto (OCA "
        "stock_inventory): crea el ajuste y lo pone en progreso para contar.",
        {"product_name": {"type": "string", "description": "Producto a contar."},
         "name": {"type": "string", "description": "Nombre del ajuste (opcional)."}},
        ["product_name"])},
    {"is_write": False, "requires": ["stock_inventory"],
     "method": "_list_inventory_adjustments", "schema": _fn(
        "list_inventory_adjustments",
        "Lista los ajustes de inventario abiertos (borrador o en progreso).",
        {})},
]

DESCRIPTIONS = {
    "validate_picking": lambda a: (
        f"Validar el albarán «{a.get('picking_name')}» (confirma el movimiento "
        f"de stock)."),
    "start_inventory_adjustment": lambda a: (
        f"Iniciar un ajuste de inventario para «{a.get('product_name')}»"
        f"{(' (' + a['name'] + ')') if a.get('name') else ''}."),
}
