from datetime import timedelta

from odoo import fields, models


class AiToolsAccount(models.AbstractModel):
    """Pack account: implementaciones (specs en ai_specs/account.py)."""

    _inherit = "odoo.ai.tools"

    def _list_unpaid_invoices(self, args):
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
        ]
        if args.get("partner_name"):
            domain.append(("partner_id.name", "ilike", args["partner_name"]))
        invs = self.env["account.move"].search(
            domain, limit=20, order="invoice_date_due asc")
        if not invs:
            return "No hay facturas de cliente pendientes de cobro."
        return "\n".join(
            f"{inv.name} — {inv.partner_id.display_name} — total {inv.amount_total} "
            f"{inv.currency_id.name} — pendiente {inv.amount_residual} — "
            f"vence {inv.invoice_date_due or '—'}"
            for inv in invs)

    def _invoice_status(self, args):
        number = (args.get("invoice_number") or "").strip()
        invs = self.env["account.move"].search(
            [("name", "ilike", number),
             ("move_type", "in", ["out_invoice", "in_invoice"])], limit=5)
        if not invs:
            return f"No se encontró ninguna factura con «{number}»."
        return "\n".join(
            f"{inv.name}: estado {inv.state}, cobro {inv.payment_state}, "
            f"pendiente {inv.amount_residual} {inv.currency_id.name}."
            for inv in invs)

    def _register_invoice_payment(self, args):
        number = (args.get("invoice_number") or "").strip()
        inv = self.env["account.move"].search(
            [("name", "ilike", number), ("move_type", "=", "out_invoice")],
            limit=1)
        if not inv:
            return f"No se encontró la factura de cliente «{number}»."
        if inv.state != "posted":
            return f"La factura {inv.name} no está validada (estado: {inv.state})."
        if inv.payment_state in ("paid", "in_payment"):
            return f"La factura {inv.name} ya está cobrada."
        wizard = (self.env["account.payment.register"]
                  .with_context(active_model="account.move", active_ids=inv.ids)
                  .create({}))
        if args.get("amount"):
            wizard.amount = float(args["amount"])
        wizard._create_payments()
        return (f"Pago registrado para {inv.name}. "
                f"Estado de cobro: {inv.payment_state}.")

    # ================== Vencimientos (Ola 6, core) ==================
    def _list_upcoming_due_dates(self, args):
        days = int(args.get("days") or 7)
        horizon = fields.Date.today() + timedelta(days=days)
        lines = self.env["account.move.line"].search([
            ("date_maturity", "!=", False),
            ("date_maturity", "<=", horizon),
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
            ("account_id.account_type",
             "in", ["asset_receivable", "liability_payable"]),
        ], limit=40, order="date_maturity asc")
        if not lines:
            return f"No hay vencimientos en los próximos {days} días."
        today = fields.Date.today()
        out = [f"Vencimientos hasta {horizon} (incluye vencidos):"]
        for ln in lines:
            kind = ("A COBRAR" if ln.account_id.account_type == "asset_receivable"
                    else "A PAGAR")
            overdue = " ⚠️ VENCIDO" if ln.date_maturity < today else ""
            out.append(
                f"- {ln.date_maturity} — {kind} — "
                f"{ln.partner_id.display_name or '—'} — "
                f"{abs(ln.amount_residual)} {ln.company_currency_id.name} — "
                f"{ln.move_id.name}{overdue}")
        return "\n".join(out)

    # ============ Extensiones OCA (Ola 6; registro condicional) ============
    def _list_payment_orders(self, args):
        # OCA account_payment_order: draft/open/generated/uploaded/cancel.
        orders = self.env["account.payment.order"].search(
            [("state", "in", ["draft", "open", "generated"])],
            limit=20, order="id desc")
        if not orders:
            return "No hay órdenes de pago abiertas."
        state_lbl = {"draft": "borrador", "open": "confirmada",
                     "generated": "fichero generado"}
        return "\n".join(
            f"{o.name} — modo: {o.payment_mode_id.name} — "
            f"{len(o.payment_line_ids)} líneas — "
            f"{o.total_company_currency} {o.company_currency_id.name} — "
            f"{state_lbl.get(o.state, o.state)}"
            for o in orders)

    def _confirm_payment_order(self, args):
        name = (args.get("order_name") or "").strip()
        order = self.env["account.payment.order"].search(
            [("name", "ilike", name)], limit=1)
        if not order:
            return f"No se encontró la orden de pago «{name}»."
        if order.state != "draft":
            return (f"La orden {order.name} no está en borrador "
                    f"(estado: {order.state}).")
        if not order.payment_line_ids:
            return f"La orden {order.name} no tiene líneas de pago."
        order.draft2open()
        return (f"Orden de pago {order.name} confirmada (estado: "
                f"{order.state}). Genera el fichero bancario desde Contabilidad.")
