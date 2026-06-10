from .common import _fn

PACK = "account"
PACK_DESCRIPTION = ("Facturación: facturas de cliente, estados de cobro y "
                    "registro de pagos.")

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
]

DESCRIPTIONS = {
    "register_invoice_payment": lambda a: (
        f"Registrar el pago de la factura «{a.get('invoice_number')}»"
        f"{(' por ' + str(a['amount'])) if a.get('amount') else ' (saldo pendiente)'}."),
}
