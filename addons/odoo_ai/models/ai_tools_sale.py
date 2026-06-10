from odoo import models


class AiToolsSale(models.AbstractModel):
    """Pack sale: implementaciones (specs en ai_specs/sale.py)."""

    _inherit = "odoo.ai.tools"

    def _find_sale_order(self, name):
        name = (name or "").strip()
        if not name:
            return "Falta el número del pedido."
        order = self.env["sale.order"].search([("name", "=", name)], limit=1)
        if not order:
            order = self.env["sale.order"].search(
                [("name", "ilike", name)], limit=1)
        if not order:
            return f"No se encontró el pedido de venta «{name}»."
        return order

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
        vals = {
            "partner_id": partner.id,
            "order_line": [(0, 0, {
                "product_id": product.id,
                "product_uom_qty": qty,
            })],
        }
        type_label = ""
        order_type = (args.get("order_type") or "").strip()
        if order_type:
            # OCA sale_order_type: campo type_id en sale.order.
            if "type_id" not in self.env["sale.order"]._fields:
                return ("Los tipos de pedido requieren el módulo OCA "
                        "sale_order_type (no instalado).")
            sot = self.env["sale.order.type"].search(
                [("name", "ilike", order_type)], limit=1)
            if not sot:
                types = self.env["sale.order.type"].search([])
                return (f"No se encontró el tipo de pedido «{order_type}». "
                        f"Disponibles: {', '.join(types.mapped('name'))}.")
            vals["type_id"] = sot.id
            type_label = f" (tipo: {sot.name})"
        order = self.env["sale.order"].create(vals)
        return (f"Presupuesto {order.name} creado para {partner.display_name}"
                f"{type_label}: {qty} × {product.display_name}. "
                f"Total: {order.amount_total} {order.currency_id.name}.")

    # ============ Extensiones OCA (Ola 3; registro condicional) ============
    def _list_sale_order_types(self, args):
        types = self.env["sale.order.type"].search([])
        if not types:
            return "No hay tipos de pedido configurados."
        return "\n".join(f"- {t.name}" for t in types)

    def _list_order_exceptions(self, args):
        # OCA sale_exception / base_exception: exception_ids en sale.order.
        res = self._find_sale_order(args.get("order_name"))
        if isinstance(res, str):
            return res
        order = res
        if order.ignore_exception:
            return f"{order.name}: las excepciones están marcadas como ignoradas."
        if not order.exception_ids:
            return f"{order.name}: sin excepciones; no está bloqueado por reglas."
        return f"Excepciones de {order.name}:\n" + "\n".join(
            f"- {e.name}{' (BLOQUEANTE)' if e.is_blocking else ''}"
            for e in order.exception_ids)

    def _list_orders_to_approve(self, args):
        # OCA base_tier_validation: can_review tiene search propio.
        orders = self.env["sale.order"].search(
            [("can_review", "=", True)], limit=20)
        orders = orders.filtered(
            lambda o: any(r.status == "pending" for r in o.review_ids))
        if not orders:
            return "No tienes pedidos de venta pendientes de aprobación."
        return "Pedidos pendientes de tu aprobación:\n" + "\n".join(
            f"- {o.name} — {o.partner_id.display_name} — {o.amount_total} "
            f"{o.currency_id.name}"
            for o in orders)

    def _approve_sale_order(self, args):
        res = self._find_sale_order(args.get("order_name"))
        if isinstance(res, str):
            return res
        order = res
        if not order.can_review:
            return (f"{order.name} no está pendiente de tu aprobación "
                    f"(o no tienes permiso para revisarlo).")
        order.validate_tier()
        return f"Pedido {order.name} aprobado."

    def _reject_sale_order(self, args):
        res = self._find_sale_order(args.get("order_name"))
        if isinstance(res, str):
            return res
        order = res
        if not order.can_review:
            return (f"{order.name} no está pendiente de tu aprobación "
                    f"(o no tienes permiso para revisarlo).")
        order.reject_tier()
        return f"Pedido {order.name} rechazado."
