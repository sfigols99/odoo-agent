from markupsafe import escape

from odoo import models


class AiToolsHelpdesk(models.AbstractModel):
    """Pack helpdesk: implementaciones (specs en ai_specs/helpdesk.py)."""

    _inherit = "odoo.ai.tools"

    def _find_ticket(self, number):
        number = (number or "").strip()
        if not number:
            return "Falta el número del ticket."
        ticket = self.env["helpdesk.ticket"].search(
            [("number", "ilike", number)], limit=1)
        if not ticket:
            return f"No se encontró el ticket «{number}»."
        return ticket

    def _create_ticket(self, args):
        vals = {
            "name": (args.get("title") or "").strip() or "Ticket",
            # description es Html: escapamos el texto del usuario/modelo.
            "description": "<p>%s</p>" % escape(args.get("description") or ""),
        }
        if args.get("customer_name"):
            partner = self.env["res.partner"].search(
                [("name", "ilike", args["customer_name"])], limit=1)
            if not partner:
                return f"No se encontró el contacto «{args['customer_name']}»."
            vals["partner_id"] = partner.id
        ticket = self.env["helpdesk.ticket"].create(vals)
        return (f"Ticket {ticket.number} creado: «{ticket.name}» "
                f"(etapa: {ticket.stage_id.name or '—'}).")

    def _list_open_tickets(self, args):
        domain = [("closed", "=", False)]
        if args.get("only_mine"):
            domain.append(("user_id", "=", self.env.user.id))
        tickets = self.env["helpdesk.ticket"].search(
            domain, limit=20, order="id desc")
        if not tickets:
            return "No hay tickets abiertos."
        return "\n".join(
            f"{t.number} — {t.name} — {t.partner_id.display_name or '—'} — "
            f"etapa: {t.stage_id.name or '—'} — "
            f"asignado: {t.user_id.name or 'sin asignar'}"
            for t in tickets)

    def _get_ticket(self, args):
        res = self._find_ticket(args.get("number"))
        if isinstance(res, str):
            return res
        t = res
        return (f"{t.number} — {t.name}\n"
                f"Contacto: {t.partner_id.display_name or t.partner_name or '—'}\n"
                f"Etapa: {t.stage_id.name or '—'} "
                f"({'cerrado' if t.closed else 'abierto'})\n"
                f"Asignado: {t.user_id.name or 'sin asignar'} — "
                f"equipo: {t.team_id.name or '—'}")

    def _assign_ticket(self, args):
        res = self._find_ticket(args.get("number"))
        if isinstance(res, str):
            return res
        ticket = res
        user = self.env["res.users"].search(
            [("name", "ilike", args.get("user") or "")], limit=1)
        if not user:
            return f"No se encontró el usuario «{args.get('user')}»."
        ticket.user_id = user.id
        return f"Ticket {ticket.number} asignado a {user.name}."

    def _close_ticket(self, args):
        res = self._find_ticket(args.get("number"))
        if isinstance(res, str):
            return res
        ticket = res
        if ticket.closed:
            return f"El ticket {ticket.number} ya está cerrado."
        stage = self.env["helpdesk.ticket.stage"].search(
            [("closed", "=", True)], limit=1, order="sequence")
        if not stage:
            return ("No hay ninguna etapa de cierre configurada en Helpdesk "
                    "(marca «closed» en alguna etapa).")
        if args.get("note"):
            ticket.message_post(body=args["note"])
        ticket.stage_id = stage.id
        return f"Ticket {ticket.number} cerrado (etapa: {stage.name})."
