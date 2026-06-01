import logging

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
}


class AiTools(models.AbstractModel):
    _name = "odoo.ai.tools"
    _description = "Registro de herramientas del Asistente IA (ORM en proceso)"

    # ---------------- Registro / despacho ----------------
    def get_tool_schemas(self):
        return [s["schema"] for s in TOOL_SPECS]

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
