from .common import _fn

PACK = "contract"
PACK_DESCRIPTION = ("Contratos recurrentes: contratos activos, renovaciones "
                    "próximas y generación de la factura del periodo.")

# Requieren OCA `contract` (alternativa gratuita a Suscripciones de
# Enterprise). Verificadas contra el código 18.0 real.
SPECS = [
    {"is_write": False, "requires": ["contract"], "method": "_list_active_contracts",
     "schema": _fn(
        "list_active_contracts",
        "Lista los contratos recurrentes activos con su próxima fecha de "
        "facturación.",
        {"partner_name": {"type": "string",
                          "description": "Filtrar por cliente (opcional)."}})},
    {"is_write": False, "requires": ["contract"], "method": "_list_contracts_to_renew",
     "schema": _fn(
        "list_contracts_to_renew",
        "Lista los contratos cuya fecha de fin cae dentro de N días "
        "(candidatos a renovación).",
        {"days": {"type": "number", "description": "Horizonte en días (por defecto 30)."}})},
    {"is_write": True, "requires": ["contract"], "method": "_generate_contract_invoice",
     "schema": _fn(
        "generate_contract_invoice",
        "Genera la factura del periodo pendiente de un contrato recurrente.",
        {"contract_name": {"type": "string", "description": "Nombre del contrato."}},
        ["contract_name"])},
]

DESCRIPTIONS = {
    "generate_contract_invoice": lambda a: (
        f"Generar la factura del periodo del contrato «{a.get('contract_name')}»."),
}
