from datetime import timedelta

from odoo import fields, models


class AiToolsCrm(models.AbstractModel):
    """Pack crm: implementaciones (specs en ai_specs/crm.py)."""

    _inherit = "odoo.ai.tools"

    def _find_customer(self, args):
        name = (args.get("name") or "").strip()
        partners = self.env["res.partner"].search(
            [("name", "ilike", name)], limit=5)
        if not partners:
            return f"No se encontró ningún contacto con «{name}»."
        return "\n".join(
            f"[{p.id}] {p.display_name}"
            f"{(' — ' + p.email) if p.email else ''}"
            f"{(' — ' + p.phone) if p.phone else ''}"
            for p in partners)

    def _list_open_opportunities(self, args):
        # type=opportunity ya excluye las perdidas (active=False). Excluimos
        # además las ganadas (probability=100) para listar solo las "abiertas".
        leads = self.env["crm.lead"].search(
            [("type", "=", "opportunity"), ("probability", "<", 100)],
            limit=20, order="expected_revenue desc")
        if not leads:
            return "No hay oportunidades abiertas visibles."
        return "\n".join(
            f"[{l.id}] {l.name} — {l.partner_id.display_name or l.contact_name or '—'} "
            f"— ingreso esperado: {l.expected_revenue} "
            f"— etapa: {l.stage_id.name}"
            for l in leads)

    def _create_lead(self, args):
        vals = {
            "name": args.get("title") or "Nuevo lead",
            "type": "lead",
        }
        if args.get("contact_name"):
            vals["contact_name"] = args["contact_name"]
        if args.get("email"):
            vals["email_from"] = args["email"]
        if args.get("description"):
            vals["description"] = args["description"]
        lead = self.env["crm.lead"].create(vals)
        return f"Lead creado con ID {lead.id}: «{lead.name}»."

    # ================== Automatizaciones del pipeline ==================
    def _find_lead(self, name, only_open=True, prefer_opportunity=True):
        """Localiza un único lead/oportunidad por nombre.

        Devuelve un recordset (1 registro) o un string de error legible si no
        hay coincidencia o si es ambigua.
        """
        name = (name or "").strip()
        if not name:
            return "Falta el nombre de la oportunidad."
        domain = [("name", "ilike", name)]
        if prefer_opportunity:
            domain = ["&", ("type", "=", "opportunity")] + domain
        leads = self.env["crm.lead"].search(domain, limit=6)
        if not leads and prefer_opportunity:
            # Reintenta incluyendo leads (no solo oportunidades).
            leads = self.env["crm.lead"].search([("name", "ilike", name)], limit=6)
        if not leads:
            return f"No se encontró ninguna oportunidad con «{name}»."
        if len(leads) > 1:
            opts = ", ".join(f"[{l.id}] {l.name}" for l in leads)
            return (f"Hay varias coincidencias para «{name}»: {opts}. "
                    f"Precisa cuál.")
        return leads

    def _get_opportunity(self, args):
        res = self._find_lead(args.get("name"))
        if isinstance(res, str):
            return res
        l = res
        act = l.activity_ids[:1]
        return (
            f"[{l.id}] {l.name} — tipo: {l.type}\n"
            f"Cliente: {l.partner_id.display_name or l.contact_name or '—'}\n"
            f"Etapa: {l.stage_id.name} — probabilidad: {l.probability}%\n"
            f"Ingreso esperado: {l.expected_revenue} {l.company_currency.name or ''}\n"
            f"Comercial: {l.user_id.name or '—'} — equipo: {l.team_id.name or '—'}\n"
            f"Próxima actividad: "
            + (f"{act.activity_type_id.name} «{act.summary or ''}» vence "
               f"{act.date_deadline}" if act else "ninguna"))

    def _convert_lead_to_opportunity(self, args):
        res = self._find_lead(args.get("name"), prefer_opportunity=False)
        if isinstance(res, str):
            return res
        lead = res
        if lead.type == "opportunity":
            return f"«{lead.name}» ya es una oportunidad."
        # Odoo 17/18: convert_opportunity recibe un RECORD de partner (no un id).
        # Gestiona asignación, etapa y vínculo de partner según la config del CRM.
        lead.convert_opportunity(lead.partner_id)
        return f"Lead «{lead.name}» convertido en oportunidad (etapa: {lead.stage_id.name})."

    def _set_opportunity_stage(self, args):
        res = self._find_lead(args.get("name"))
        if isinstance(res, str):
            return res
        lead = res
        stage_name = (args.get("stage_name") or "").strip()
        stage = self.env["crm.stage"].search(
            [("name", "ilike", stage_name)], limit=1)
        if not stage:
            stages = self.env["crm.stage"].search([])
            return (f"No se encontró la etapa «{stage_name}». "
                    f"Disponibles: {', '.join(stages.mapped('name'))}.")
        lead.stage_id = stage.id
        return f"«{lead.name}» movida a la etapa «{stage.name}»."

    def _mark_opportunity_won(self, args):
        res = self._find_lead(args.get("name"))
        if isinstance(res, str):
            return res
        lead = res
        lead.action_set_won()
        return f"Oportunidad «{lead.name}» marcada como ganada (prob. {lead.probability}%)."

    def _mark_opportunity_lost(self, args):
        res = self._find_lead(args.get("name"))
        if isinstance(res, str):
            return res
        lead = res
        reason = (args.get("reason") or "").strip()
        ctx = {}
        if reason:
            lost = self.env["crm.lost.reason"].search(
                [("name", "ilike", reason)], limit=1)
            if not lost:
                lost = self.env["crm.lost.reason"].create({"name": reason})
            ctx["default_lost_reason_id"] = lost.id
        # action_set_lost acepta lost_reason_id como kwarg en Odoo 16+.
        if ctx:
            lead.action_set_lost(lost_reason_id=ctx["default_lost_reason_id"])
        else:
            lead.action_set_lost()
        return (f"Oportunidad «{lead.name}» marcada como perdida"
                f"{(' (motivo: ' + reason + ')') if reason else ''}.")

    def _assign_opportunity(self, args):
        res = self._find_lead(args.get("name"))
        if isinstance(res, str):
            return res
        lead = res
        vals = {}
        done = []
        if args.get("salesperson"):
            user = self.env["res.users"].search(
                [("name", "ilike", args["salesperson"])], limit=1)
            if not user:
                return f"No se encontró el comercial «{args['salesperson']}»."
            vals["user_id"] = user.id
            done.append(f"comercial {user.name}")
        if args.get("sales_team"):
            team = self.env["crm.team"].search(
                [("name", "ilike", args["sales_team"])], limit=1)
            if not team:
                return f"No se encontró el equipo «{args['sales_team']}»."
            vals["team_id"] = team.id
            done.append(f"equipo {team.name}")
        if not vals:
            return "Indica un comercial y/o un equipo de ventas."
        lead.write(vals)
        return f"«{lead.name}» asignada a {', '.join(done)}."

    def _schedule_activity(self, args):
        res = self._find_lead(args.get("name"))
        if isinstance(res, str):
            return res
        lead = res
        # Mapeo de tipos amigables a los xmlid estándar de mail.activity.type.
        type_xmlids = {
            "call": "mail.mail_activity_data_call",
            "meeting": "mail.mail_activity_data_meeting",
            "todo": "mail.mail_activity_data_todo",
            "email": "mail.mail_activity_data_email",
        }
        key = (args.get("activity_type") or "todo").lower()
        xmlid = type_xmlids.get(key, type_xmlids["todo"])
        act_type = self.env.ref(xmlid, raise_if_not_found=False)
        due = fields.Date.today() + timedelta(days=int(args.get("due_in_days") or 1))
        lead.activity_schedule(
            act_type_xmlid=xmlid if act_type else False,
            date_deadline=due,
            summary=args.get("summary") or "",
        )
        return (f"Actividad «{key}» programada sobre «{lead.name}» para {due}: "
                f"{args.get('summary') or ''}.")

    def _log_note(self, args):
        res = self._find_lead(args.get("name"))
        if isinstance(res, str):
            return res
        lead = res
        note = (args.get("note") or "").strip()
        if not note:
            return "La nota está vacía."
        lead.message_post(body=note)
        return f"Nota registrada en «{lead.name}»."

    def _update_opportunity_fields(self, args):
        res = self._find_lead(args.get("name"))
        if isinstance(res, str):
            return res
        lead = res
        vals = {}
        if args.get("expected_revenue") is not None:
            vals["expected_revenue"] = float(args["expected_revenue"])
        if args.get("probability") is not None:
            vals["probability"] = max(0.0, min(100.0, float(args["probability"])))
        if args.get("priority"):
            # crm.lead.priority: 0=low,1=medium,2=high,3=very_high.
            prio_map = {"low": "0", "medium": "1", "high": "2", "very_high": "3"}
            p = prio_map.get(str(args["priority"]).lower())
            if p is None:
                return ("Prioridad no válida: usa low, medium, high o very_high.")
            vals["priority"] = p
        if args.get("tags"):
            tag_ids = []
            for t in args["tags"]:
                tag = self.env["crm.tag"].search([("name", "ilike", t)], limit=1)
                if not tag:
                    tag = self.env["crm.tag"].create({"name": t})
                tag_ids.append(tag.id)
            vals["tag_ids"] = [(6, 0, tag_ids)]
        if not vals:
            return "No se indicó ningún campo a actualizar."
        lead.write(vals)
        return f"«{lead.name}» actualizada: {', '.join(vals.keys())}."

    def _list_stale_opportunities(self, args):
        days = int(args.get("days") or 14)
        cutoff = fields.Datetime.now() - timedelta(days=days)
        # Abiertas, sin próxima actividad planificada y sin cambios recientes.
        leads = self.env["crm.lead"].search([
            ("type", "=", "opportunity"),
            ("probability", "<", 100),
            ("activity_ids", "=", False),
            ("write_date", "<", cutoff),
        ], limit=20, order="write_date asc")
        if not leads:
            return (f"No hay oportunidades estancadas (>{days} días sin "
                    f"actividad ni cambios).")
        return "Oportunidades estancadas (propón la siguiente acción):\n" + "\n".join(
            f"[{l.id}] {l.name} — etapa: {l.stage_id.name} — "
            f"último cambio: {l.write_date.date()} — comercial: {l.user_id.name or '—'}"
            for l in leads)

    def _find_duplicate_opportunities(self, args):
        term = (args.get("name") or "").strip()
        if not term:
            return "Indica un email o nombre de contacto a comprobar."
        domain = ["|", ("email_from", "ilike", term),
                  ("contact_name", "ilike", term)]
        leads = self.env["crm.lead"].search(domain, limit=20, order="create_date desc")
        if len(leads) < 2:
            return f"No se encontraron duplicados para «{term}»."
        return (f"Posibles duplicados para «{term}» ({len(leads)}):\n" + "\n".join(
            f"[{l.id}] {l.name} — {l.email_from or l.contact_name or '—'} — "
            f"etapa: {l.stage_id.name} — creado: {l.create_date.date()}"
            for l in leads))
