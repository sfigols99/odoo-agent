from .common import _fn

PACK = "helpdesk"
PACK_DESCRIPTION = ("Soporte/helpdesk: crear, consultar, asignar y cerrar "
                    "tickets de soporte.")

# Todas requieren OCA helpdesk_mgmt (alternativa gratuita al Helpdesk de
# Enterprise). Verificadas contra el código 18.0 real.
SPECS = [
    {"is_write": True, "requires": ["helpdesk_mgmt"], "method": "_create_ticket",
     "schema": _fn(
        "create_ticket",
        "Crea un ticket de soporte.",
        {"title": {"type": "string", "description": "Título del ticket."},
         "description": {"type": "string", "description": "Descripción del problema."},
         "customer_name": {"type": "string",
                           "description": "Cliente/contacto afectado (opcional)."}},
        ["title", "description"])},
    {"is_write": False, "requires": ["helpdesk_mgmt"], "method": "_list_open_tickets",
     "schema": _fn(
        "list_open_tickets",
        "Lista los tickets de soporte abiertos (no cerrados).",
        {"only_mine": {"type": "boolean",
                       "description": "Solo los asignados a mí (por defecto false)."}})},
    {"is_write": False, "requires": ["helpdesk_mgmt"], "method": "_get_ticket",
     "schema": _fn(
        "get_ticket",
        "Devuelve el detalle de un ticket por su número.",
        {"number": {"type": "string", "description": "Número del ticket."}},
        ["number"])},
    {"is_write": True, "requires": ["helpdesk_mgmt"], "method": "_assign_ticket",
     "schema": _fn(
        "assign_ticket",
        "Asigna un ticket de soporte a un usuario.",
        {"number": {"type": "string", "description": "Número del ticket."},
         "user": {"type": "string", "description": "Nombre del usuario asignado."}},
        ["number", "user"])},
    {"is_write": True, "requires": ["helpdesk_mgmt"], "method": "_close_ticket",
     "schema": _fn(
        "close_ticket",
        "Cierra un ticket de soporte (lo mueve a una etapa cerrada).",
        {"number": {"type": "string", "description": "Número del ticket."},
         "note": {"type": "string", "description": "Nota de cierre (opcional)."}},
        ["number"])},
]

DESCRIPTIONS = {
    "create_ticket": lambda a: (
        f"Crear un ticket de soporte: «{a.get('title')}»"
        f"{(' para ' + a['customer_name']) if a.get('customer_name') else ''}."),
    "assign_ticket": lambda a: (
        f"Asignar el ticket «{a.get('number')}» a {a.get('user')}."),
    "close_ticket": lambda a: (
        f"CERRAR el ticket «{a.get('number')}»"
        f"{(' — ' + a['note']) if a.get('note') else ''}."),
}
