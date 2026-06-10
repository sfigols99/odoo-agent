from odoo import models


class AiToolsStock(models.AbstractModel):
    """Pack stock: implementaciones (specs en ai_specs/stock.py)."""

    _inherit = "odoo.ai.tools"

    def _check_stock(self, args):
        name = (args.get("product_name") or "").strip()
        if not name:
            return "Falta el nombre del producto."
        prods = self.env["product.product"].search(
            [("name", "ilike", name)], limit=5)
        if not prods:
            return f"No se encontró ningún producto que coincida con «{name}»."
        return "\n".join(
            f"{p.display_name}: {p.qty_available} a mano, {p.free_qty} libres, "
            f"{p.virtual_available} previstas (UoM: {p.uom_id.name})."
            for p in prods)

    def _list_low_stock(self, args):
        threshold = float(args.get("threshold") or 5)
        # En Odoo 17/18 los tipos product/consu se fusionaron y la
        # "almacenabilidad" pasó al booleano is_storable; solo esos productos
        # tienen stock real que controlar. Filtramos en el dominio para no
        # perder coincidencias más allá del límite de búsqueda.
        prods = self.env["product.product"].search(
            [("is_storable", "=", True), ("qty_available", "<=", threshold)],
            limit=30, order="qty_available asc")
        if not prods:
            return f"No hay productos con stock por debajo de {threshold}."
        return "\n".join(
            f"{p.display_name}: {p.qty_available}" for p in prods)
