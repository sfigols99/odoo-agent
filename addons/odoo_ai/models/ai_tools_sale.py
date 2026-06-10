from odoo import models


class AiToolsSale(models.AbstractModel):
    """Pack sale: implementaciones (specs en ai_specs/sale.py)."""

    _inherit = "odoo.ai.tools"

    def _create_quotation(self, args):
        partner = self.env["res.partner"].search(
            [("name", "ilike", args.get("customer_name") or "")], limit=1)
        if not partner:
            return f"No se encontró el cliente «{args.get('customer_name')}»."
        product = self.env["product.product"].search(
            [("name", "ilike", args.get("product_name") or "")], limit=1)
        if not product:
            return f"No se encontró el producto «{args.get('product_name')}»."
        qty = float(args.get("quantity") or 1)
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "order_line": [(0, 0, {
                "product_id": product.id,
                "product_uom_qty": qty,
            })],
        })
        return (f"Presupuesto {order.name} creado para {partner.display_name}: "
                f"{qty} × {product.display_name}. Total: {order.amount_total} "
                f"{order.currency_id.name}.")
