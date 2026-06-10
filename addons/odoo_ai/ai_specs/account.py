from .common import _fn

PACK = "account"
PACK_DESCRIPTION = ("Facturación y finanzas: facturas de cliente, estados de "
                    "cobro, pagos, vencimientos próximos y remesas/órdenes "
                    "de pago.")

SPECS = [
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
    # ---------------- Vencimientos (Ola 6, core) ----------------
    {"is_write": False, "method": "_list_upcoming_due_dates", "schema": _fn(
        "list_upcoming_due_dates",
        "Lista los vencimientos próximos: importes a cobrar y a pagar con "
        "fecha de vencimiento dentro de N días (incluye los ya vencidos).",
        {"days": {"type": "number", "description": "Horizonte en días (por defecto 7)."}})},
    # ---------------- Extensiones OCA (Ola 6) ----------------
    # account_payment_order verificado contra el código 18.0 real (estados
    # draft/open/generated/uploaded; transición draft2open).
    {"is_write": False, "requires": ["account_payment_order"],
     "method": "_list_payment_orders", "schema": _fn(
        "list_payment_orders",
        "Lista las órdenes/remesas de pago abiertas y su estado.",
        {})},
    {"is_write": True, "requires": ["account_payment_order"],
     "method": "_confirm_payment_order", "schema": _fn(
        "confirm_payment_order",
        "Confirma una orden/remesa de pago en borrador (paso previo a generar "
        "el fichero bancario).",
        {"order_name": {"type": "string",
                        "description": "Referencia de la orden (p. ej. PAY0007)."}},
        ["order_name"])},
]

DESCRIPTIONS = {
    "register_invoice_payment": lambda a: (
        f"Registrar el pago de la factura «{a.get('invoice_number')}»"
        f"{(' por ' + str(a['amount'])) if a.get('amount') else ' (saldo pendiente)'}."),
    "confirm_payment_order": lambda a: (
        f"Confirmar la orden de pago «{a.get('order_name')}»."),
}
