from odoo import fields, models


class AiToolsPurchase(models.AbstractModel):
    """Pack purchase: implementaciones (specs en ai_specs/purchase.py)."""

    _inherit = "odoo.ai.tools"

    def _list_open_purchase_orders(self, args):
        pos = self.env["purchase.order"].search(
            [("state", "in", ["draft", "sent", "to approve", "purchase"])],
            limit=20, order="date_order desc")
        if not pos:
            return "No hay pedidos de compra abiertos."
        return "\n".join(
            f"{po.name} — {po.partner_id.display_name} — {po.amount_total} "
            f"{po.currency_id.name} — estado: {po.state}"
            for po in pos)

    def _create_purchase_order(self, args):
        vendor = self.env["res.partner"].search(
            [("name", "ilike", args.get("vendor_name") or "")], limit=1)
        if not vendor:
            return f"No se encontró el proveedor «{args.get('vendor_name')}»."
        product = self.env["product.product"].search(
            [("name", "ilike", args.get("product_name") or "")], limit=1)
        if not product:
            return f"No se encontró el producto «{args.get('product_name')}»."
        qty = float(args.get("quantity") or 1)
        po = self.env["purchase.order"].create({
            "partner_id": vendor.id,
            "order_line": [(0, 0, {
                "name": product.display_name,
                "product_id": product.id,
                "product_qty": qty,
                # En purchase.order.line de Odoo 18 el campo de UoM es
                # product_uom (no product_uom_id, que sí existe en sale.order.line).
                "product_uom": (product.uom_po_id or product.uom_id).id,
                "price_unit": product.standard_price,
                "date_planned": fields.Datetime.now(),
            })],
        })
        return (f"Pedido de compra {po.name} creado para {vendor.display_name}: "
                f"{qty} × {product.display_name}. Total: {po.amount_total} "
                f"{po.currency_id.name}. (Sin confirmar.)")

    def _confirm_purchase_order(self, args):
        name = (args.get("po_name") or "").strip()
        po = self.env["purchase.order"].search([("name", "=", name)], limit=1)
        if not po:
            return f"No se encontró el pedido de compra «{name}»."
        if po.state in ("purchase", "done"):
            return f"El pedido {po.name} ya está confirmado (estado: {po.state})."
        po.button_confirm()
        return f"Pedido de compra {po.name} confirmado. Estado: {po.state}."
