from odoo import models


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
