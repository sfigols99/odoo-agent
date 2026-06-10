from datetime import timedelta

from odoo import fields, models


class AiToolsContract(models.AbstractModel):
    """Pack contract: implementaciones (specs en ai_specs/contract.py)."""

    _inherit = "odoo.ai.tools"

    def _list_active_contracts(self, args):
        domain = []
        if args.get("partner_name"):
            domain.append(("partner_id.name", "ilike", args["partner_name"]))
        contracts = self.env["contract.contract"].search(
            domain, limit=20, order="recurring_next_date asc")
        if not contracts:
            return "No hay contratos activos."
        return "\n".join(
            f"[{c.id}] {c.name} — {c.partner_id.display_name} — "
            f"próxima factura: {c.recurring_next_date or '—'} — "
            f"fin: {c.date_end or 'indefinido'}"
            for c in contracts)

    def _list_contracts_to_renew(self, args):
        days = int(args.get("days") or 30)
        horizon = fields.Date.today() + timedelta(days=days)
        contracts = self.env["contract.contract"].search(
            [("date_end", "!=", False), ("date_end", "<=", horizon)],
            limit=20, order="date_end asc")
        if not contracts:
            return f"Ningún contrato termina en los próximos {days} días."
        return (f"Contratos que terminan antes de {horizon} (renovar):\n"
                + "\n".join(
                    f"[{c.id}] {c.name} — {c.partner_id.display_name} — "
                    f"fin: {c.date_end}"
                    for c in contracts))

    def _generate_contract_invoice(self, args):
        name = (args.get("contract_name") or "").strip()
        if not name:
            return "Falta el nombre del contrato."
        contract = self.env["contract.contract"].search(
            [("name", "ilike", name)], limit=1)
        if not contract:
            return f"No se encontró el contrato «{name}»."
        if not contract.recurring_next_date:
            return (f"El contrato «{contract.name}» no tiene próxima fecha de "
                    f"facturación (sin líneas recurrentes pendientes).")
        if contract.recurring_next_date > fields.Date.today():
            return (f"El periodo del contrato «{contract.name}» aún no ha "
                    f"vencido (próxima factura: {contract.recurring_next_date}). "
                    f"No se ha generado nada.")
        moves = contract.recurring_create_invoice()
        if not moves:
            return (f"No se generó ninguna factura para «{contract.name}» "
                    f"(revisa las líneas del contrato).")
        return (f"Factura(s) {', '.join(moves.mapped('name'))} generada(s) "
                f"para el contrato «{contract.name}». Próxima factura: "
                f"{contract.recurring_next_date or '—'}.")
