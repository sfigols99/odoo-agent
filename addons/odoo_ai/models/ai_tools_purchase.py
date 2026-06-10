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
        vals = {
            "partner_id": vendor.id,
            "order_line": [(0, 0, {
                "name": product.display_name,
                "product_id": product.id,
                "product_qty": qty,
                # Odoo 17/18 renombró product_uom -> product_uom_id en las líneas.
                "product_uom_id": (product.uom_po_id or product.uom_id).id,
                "price_unit": product.standard_price,
                "date_planned": fields.Datetime.now(),
            })],
        }
        type_label = ""
        order_type = (args.get("order_type") or "").strip()
        if order_type:
            # OCA purchase_order_type: campo order_type en purchase.order.
            if "order_type" not in self.env["purchase.order"]._fields:
                return ("Los tipos de pedido de compra requieren el módulo OCA "
                        "purchase_order_type (no instalado).")
            pot = self.env["purchase.order.type"].search(
                [("name", "ilike", order_type)], limit=1)
            if not pot:
                types = self.env["purchase.order.type"].search([])
                return (f"No se encontró el tipo «{order_type}». "
                        f"Disponibles: {', '.join(types.mapped('name'))}.")
            vals["order_type"] = pot.id
            type_label = f" (tipo: {pot.name})"
        po = self.env["purchase.order"].create(vals)
        return (f"Pedido de compra {po.name} creado para {vendor.display_name}"
                f"{type_label}: {qty} × {product.display_name}. "
                f"Total: {po.amount_total} {po.currency_id.name}. (Sin confirmar.)")

    def _confirm_purchase_order(self, args):
        name = (args.get("po_name") or "").strip()
        po = self.env["purchase.order"].search([("name", "=", name)], limit=1)
        if not po:
            return f"No se encontró el pedido de compra «{name}»."
        if po.state in ("purchase", "done"):
            return f"El pedido {po.name} ya está confirmado (estado: {po.state})."
        po.button_confirm()
        return f"Pedido de compra {po.name} confirmado. Estado: {po.state}."

    # ============ Extensiones OCA (Ola 5; registro condicional) ============
    def _create_purchase_request(self, args):
        # OCA purchase_request: draft -> to_approve -> approved/rejected.
        product = self.env["product.product"].search(
            [("name", "ilike", args.get("product_name") or "")], limit=1)
        if not product:
            return f"No se encontró el producto «{args.get('product_name')}»."
        qty = float(args.get("quantity") or 1)
        req = self.env["purchase.request"].create({
            "line_ids": [(0, 0, {
                "product_id": product.id,
                "product_qty": qty,
                "name": (args.get("reason")
                         or product.display_name),
            })],
        })
        req.button_to_approve()
        return (f"Solicitud de compra {req.name} creada y enviada a "
                f"aprobación: {qty} × {product.display_name} "
                f"(estado: {req.state}).")

    def _list_purchase_requests(self, args):
        reqs = self.env["purchase.request"].search(
            [("state", "in", ["draft", "to_approve", "approved"])],
            limit=20, order="id desc")
        if not reqs:
            return "No hay solicitudes de compra abiertas."
        state_lbl = {"draft": "borrador", "to_approve": "por aprobar",
                     "approved": "aprobada"}
        return "\n".join(
            f"{r.name} — solicitada por {r.requested_by.name or '—'} — "
            f"{state_lbl.get(r.state, r.state)} — "
            + "; ".join(f"{ln.product_qty} × {ln.product_id.display_name or ln.name}"
                        for ln in r.line_ids[:3])
            for r in reqs)

    def _approve_purchase_request(self, args):
        name = (args.get("request_name") or "").strip()
        req = self.env["purchase.request"].search(
            [("name", "ilike", name)], limit=1)
        if not req:
            return f"No se encontró la solicitud «{name}»."
        if req.state != "to_approve":
            return (f"La solicitud {req.name} no está pendiente de aprobación "
                    f"(estado: {req.state}).")
        req.button_approved()
        return f"Solicitud {req.name} aprobada."
