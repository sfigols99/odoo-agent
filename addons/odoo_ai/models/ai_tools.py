import logging
from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


def _fn(name, description, properties, required=None):
    """Construye un schema de función en formato OpenAI / vLLM."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


# Registro declarativo: nombre -> {schema, método, escritura?}.
# El nombre de cada tool vive dentro de schema["function"]["name"].
TOOL_SPECS = [
    # ---------------- Inventario / Stock (lectura) ----------------
    {"is_write": False, "method": "_check_stock", "schema": _fn(
        "check_stock",
        "Consulta el stock disponible de un producto por nombre.",
        {"product_name": {"type": "string",
                          "description": "Nombre o parte del nombre del producto."}},
        ["product_name"])},
    {"is_write": False, "method": "_list_low_stock", "schema": _fn(
        "list_low_stock",
        "Lista productos con stock a mano por debajo de un umbral.",
        {"threshold": {"type": "number",
                       "description": "Umbral de unidades (por defecto 5)."}})},
    # ---------------- CRM / Ventas ----------------
    {"is_write": False, "method": "_find_customer", "schema": _fn(
        "find_customer",
        "Busca clientes/contactos (res.partner) por nombre.",
        {"name": {"type": "string", "description": "Nombre a buscar."}},
        ["name"])},
    {"is_write": False, "method": "_list_open_opportunities", "schema": _fn(
        "list_open_opportunities",
        "Lista las oportunidades de CRM abiertas visibles para el usuario.",
        {})},
    {"is_write": True, "method": "_create_lead", "schema": _fn(
        "create_lead",
        "Crea un lead/oportunidad en el CRM.",
        {"title": {"type": "string", "description": "Título del lead."},
         "contact_name": {"type": "string", "description": "Nombre del contacto."},
         "email": {"type": "string", "description": "Email del contacto."},
         "description": {"type": "string", "description": "Notas opcionales."}},
        ["title"])},
    {"is_write": True, "method": "_create_quotation", "schema": _fn(
        "create_quotation",
        "Crea un presupuesto de venta con una línea de producto.",
        {"customer_name": {"type": "string", "description": "Nombre del cliente."},
         "product_name": {"type": "string", "description": "Nombre del producto."},
         "quantity": {"type": "number", "description": "Cantidad (por defecto 1)."}},
        ["customer_name", "product_name"])},
    # ---------------- CRM: automatizaciones del pipeline ----------------
    # Todas declaran requires=["crm"] (dependencia dura del módulo, ya en el
    # manifest) para servir de ejemplo del registro condicional; las tools de
    # extensiones OCA usarán el mismo mecanismo con su módulo correspondiente.
    {"is_write": False, "requires": ["crm"], "method": "_get_opportunity",
     "schema": _fn(
        "get_opportunity",
        "Busca una oportunidad/lead del CRM por nombre y devuelve su detalle "
        "(etapa, comercial, importe, probabilidad, próxima actividad).",
        {"name": {"type": "string", "description": "Nombre (o parte) de la oportunidad."}},
        ["name"])},
    # -- Ciclo de vida --
    {"is_write": True, "requires": ["crm"], "method": "_convert_lead_to_opportunity",
     "schema": _fn(
        "convert_lead_to_opportunity",
        "Convierte un lead en oportunidad.",
        {"name": {"type": "string", "description": "Nombre (o parte) del lead."}},
        ["name"])},
    {"is_write": True, "requires": ["crm"], "method": "_set_opportunity_stage",
     "schema": _fn(
        "set_opportunity_stage",
        "Mueve una oportunidad a una etapa del pipeline por nombre de etapa.",
        {"name": {"type": "string", "description": "Nombre (o parte) de la oportunidad."},
         "stage_name": {"type": "string", "description": "Nombre de la etapa destino."}},
        ["name", "stage_name"])},
    {"is_write": True, "requires": ["crm"], "method": "_mark_opportunity_won",
     "schema": _fn(
        "mark_opportunity_won",
        "Marca una oportunidad como ganada.",
        {"name": {"type": "string", "description": "Nombre (o parte) de la oportunidad."}},
        ["name"])},
    {"is_write": True, "requires": ["crm"], "method": "_mark_opportunity_lost",
     "schema": _fn(
        "mark_opportunity_lost",
        "Marca una oportunidad como perdida, con un motivo opcional.",
        {"name": {"type": "string", "description": "Nombre (o parte) de la oportunidad."},
         "reason": {"type": "string", "description": "Motivo de pérdida (crm.lost.reason)."}},
        ["name"])},
    # -- Asignación y actividades --
    {"is_write": True, "requires": ["crm"], "method": "_assign_opportunity",
     "schema": _fn(
        "assign_opportunity",
        "Asigna una oportunidad a un comercial y/o a un equipo de ventas.",
        {"name": {"type": "string", "description": "Nombre (o parte) de la oportunidad."},
         "salesperson": {"type": "string", "description": "Nombre del comercial (res.users)."},
         "sales_team": {"type": "string", "description": "Nombre del equipo (crm.team)."}},
        ["name"])},
    {"is_write": True, "requires": ["crm"], "method": "_schedule_activity",
     "schema": _fn(
        "schedule_activity",
        "Programa una actividad (llamada, reunión, tarea, email) sobre una "
        "oportunidad, con fecha de vencimiento y resumen.",
        {"name": {"type": "string", "description": "Nombre (o parte) de la oportunidad."},
         "summary": {"type": "string", "description": "Resumen de la actividad."},
         "activity_type": {"type": "string",
                           "description": "Tipo: call, meeting, todo o email (por defecto todo)."},
         "due_in_days": {"type": "number",
                         "description": "Días hasta el vencimiento (por defecto 1)."}},
        ["name", "summary"])},
    {"is_write": True, "requires": ["crm"], "method": "_log_note",
     "schema": _fn(
        "log_note",
        "Registra una nota interna en el historial (chatter) de una oportunidad.",
        {"name": {"type": "string", "description": "Nombre (o parte) de la oportunidad."},
         "note": {"type": "string", "description": "Texto de la nota."}},
        ["name", "note"])},
    # -- Enriquecimiento --
    {"is_write": True, "requires": ["crm"], "method": "_update_opportunity_fields",
     "schema": _fn(
        "update_opportunity_fields",
        "Actualiza campos de una oportunidad: ingreso esperado, probabilidad, "
        "prioridad y/o etiquetas.",
        {"name": {"type": "string", "description": "Nombre (o parte) de la oportunidad."},
         "expected_revenue": {"type": "number", "description": "Ingreso esperado."},
         "probability": {"type": "number", "description": "Probabilidad 0-100."},
         "priority": {"type": "string",
                      "description": "Prioridad: low, medium, high o very_high."},
         "tags": {"type": "array", "items": {"type": "string"},
                  "description": "Etiquetas (crm.tag); se crean si no existen."}},
        ["name"])},
    # -- Higiene de pipeline --
    {"is_write": False, "requires": ["crm"], "method": "_list_stale_opportunities",
     "schema": _fn(
        "list_stale_opportunities",
        "Lista oportunidades abiertas sin actividad planificada o estancadas "
        "(sin cambios) durante más de N días, para proponer la siguiente acción.",
        {"days": {"type": "number", "description": "Umbral de días (por defecto 14)."}})},
    {"is_write": False, "requires": ["crm"], "method": "_find_duplicate_opportunities",
     "schema": _fn(
        "find_duplicate_opportunities",
        "Busca posibles oportunidades duplicadas por email o por nombre de contacto.",
        {"name": {"type": "string",
                  "description": "Email o nombre de contacto a comprobar."}},
        ["name"])},
    # ---------------- Facturación / Contabilidad ----------------
    {"is_write": False, "method": "_list_unpaid_invoices", "schema": _fn(
        "list_unpaid_invoices",
        "Lista facturas de cliente validadas y pendientes de cobro.",
        {"partner_name": {"type": "string",
                          "description": "Filtrar por nombre de cliente (opcional)."}})},
    {"is_write": False, "method": "_invoice_status", "schema": _fn(
        "invoice_status",
        "Devuelve el estado y el saldo pendiente de una factura por su número.",
        {"invoice_number": {"type": "string", "description": "Número/referencia de la factura."}},
        ["invoice_number"])},
    {"is_write": True, "method": "_register_invoice_payment", "schema": _fn(
        "register_invoice_payment",
        "Registra el pago de una factura de cliente validada.",
        {"invoice_number": {"type": "string", "description": "Número de la factura."},
         "amount": {"type": "number", "description": "Importe (por defecto, el saldo pendiente)."}},
        ["invoice_number"])},
    # ---------------- Compras / Proveedores ----------------
    {"is_write": False, "method": "_list_open_purchase_orders", "schema": _fn(
        "list_open_purchase_orders",
        "Lista los pedidos de compra que no están finalizados ni cancelados.",
        {})},
    {"is_write": True, "method": "_create_purchase_order", "schema": _fn(
        "create_purchase_order",
        "Crea un pedido de compra (RFQ) con una línea de producto.",
        {"vendor_name": {"type": "string", "description": "Nombre del proveedor."},
         "product_name": {"type": "string", "description": "Nombre del producto."},
         "quantity": {"type": "number", "description": "Cantidad (por defecto 1)."}},
        ["vendor_name", "product_name"])},
    {"is_write": True, "method": "_confirm_purchase_order", "schema": _fn(
        "confirm_purchase_order",
        "Confirma un pedido de compra existente por su número.",
        {"po_name": {"type": "string", "description": "Número del pedido de compra (p. ej. P00012)."}},
        ["po_name"])},
]

# Descripciones legibles para la tarjeta de confirmación de la UI.
DESCRIPTIONS = {
    "create_lead": lambda a: (
        f"Crear un lead CRM: «{a.get('title')}»"
        f"{(' — contacto: ' + a['contact_name']) if a.get('contact_name') else ''}"
        f"{(' — email: ' + a['email']) if a.get('email') else ''}."),
    "create_quotation": lambda a: (
        f"Crear un presupuesto para «{a.get('customer_name')}»: "
        f"{a.get('quantity', 1)} × «{a.get('product_name')}»."),
    "register_invoice_payment": lambda a: (
        f"Registrar el pago de la factura «{a.get('invoice_number')}»"
        f"{(' por ' + str(a['amount'])) if a.get('amount') else ' (saldo pendiente)'}."),
    "create_purchase_order": lambda a: (
        f"Crear un pedido de compra a «{a.get('vendor_name')}»: "
        f"{a.get('quantity', 1)} × «{a.get('product_name')}»."),
    "confirm_purchase_order": lambda a: (
        f"Confirmar el pedido de compra «{a.get('po_name')}»."),
    # ---- CRM ----
    "convert_lead_to_opportunity": lambda a: (
        f"Convertir el lead «{a.get('name')}» en oportunidad."),
    "set_opportunity_stage": lambda a: (
        f"Mover «{a.get('name')}» a la etapa «{a.get('stage_name')}»."),
    "mark_opportunity_won": lambda a: (
        f"Marcar la oportunidad «{a.get('name')}» como GANADA."),
    "mark_opportunity_lost": lambda a: (
        f"Marcar «{a.get('name')}» como PERDIDA"
        f"{(' (motivo: ' + a['reason'] + ')') if a.get('reason') else ''}."),
    "assign_opportunity": lambda a: (
        f"Asignar «{a.get('name')}»"
        f"{(' al comercial ' + a['salesperson']) if a.get('salesperson') else ''}"
        f"{(' al equipo ' + a['sales_team']) if a.get('sales_team') else ''}."),
    "schedule_activity": lambda a: (
        f"Programar «{a.get('activity_type', 'todo')}» sobre «{a.get('name')}»: "
        f"{a.get('summary')} (vence en {a.get('due_in_days', 1)} día(s))."),
    "log_note": lambda a: (
        f"Registrar una nota en «{a.get('name')}»: {a.get('note')}"),
    "update_opportunity_fields": lambda a: (
        f"Actualizar «{a.get('name')}»: "
        + ", ".join(
            f"{k}={a[k]}" for k in
            ("expected_revenue", "probability", "priority", "tags")
            if a.get(k) is not None) + "."),
}


class AiTools(models.AbstractModel):
    _name = "odoo.ai.tools"
    _description = "Registro de herramientas del Asistente IA (ORM en proceso)"

    # ---------------- Registro condicional / despacho ----------------
    def _installed_modules(self):
        """Conjunto de módulos instalados (cacheado por petición)."""
        mods = self.env["ir.module.module"].sudo().search(
            [("state", "=", "installed")])
        return set(mods.mapped("name"))

    def _is_available(self, spec, installed=None):
        """Una tool está disponible si todos sus módulos `requires` lo están.

        Las tools sin `requires` (core: stock, account, purchase...) siempre
        están disponibles. Este es el punto de extensión para integrar módulos
        OCA: cada tool nueva declara `requires=["nombre_modulo_oca"]` y solo
        aparece cuando ese módulo está instalado.
        """
        requires = spec.get("requires")
        if not requires:
            return True
        if installed is None:
            installed = self._installed_modules()
        return all(m in installed for m in requires)

    def _available_specs(self):
        installed = self._installed_modules()
        return [s for s in TOOL_SPECS if self._is_available(s, installed)]

    def get_tool_schemas(self):
        # Solo se exponen al LLM las tools cuyos módulos están instalados.
        return [s["schema"] for s in self._available_specs()]

    def _spec(self, name):
        return next(
            (s for s in TOOL_SPECS if s["schema"]["function"]["name"] == name),
            None,
        )

    def is_write_tool(self, name):
        spec = self._spec(name)
        return bool(spec and spec["is_write"])

    def describe_action(self, name, args):
        fmt = DESCRIPTIONS.get(name)
        return fmt(args or {}) if fmt else f"Ejecutar «{name}» con {args}."

    def execute_tool(self, name, args):
        spec = self._spec(name)
        if not spec:
            return f"Error: herramienta desconocida «{name}»."
        if not self._is_available(spec):
            return (f"La herramienta «{name}» no está disponible: requiere los "
                    f"módulos {spec.get('requires')} (no instalados).")
        method = getattr(self, spec["method"], None)
        if method is None:
            return f"Error: implementación no encontrada para «{name}»."
        try:
            return method(args or {})
        except (AccessError, UserError, ValidationError) as e:
            return f"No se pudo completar: {e}"
        except Exception as e:  # noqa: BLE001 - se devuelve al modelo como texto
            _logger.exception("Tool %s falló", name)
            return f"Error ejecutando «{name}»: {e}"

    # ================== Inventario / Stock ==================
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

    # ================== CRM / Ventas ==================
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

    # ================== CRM: automatizaciones del pipeline ==================
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

    # ================== Facturación / Contabilidad ==================
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

    # ================== Compras / Proveedores ==================
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
                # Odoo 17/18 renombró product_uom -> product_uom_id en las líneas.
                "product_uom_id": (product.uom_po_id or product.uom_id).id,
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
