from .common import _fn

PACK = "crm"
PACK_DESCRIPTION = ("CRM: contactos, leads y oportunidades — buscar, crear, "
                    "etapas, ganar/perder, asignar, actividades, notas, "
                    "estancadas y duplicados.")

SPECS = [
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
    # ---------------- Automatizaciones del pipeline ----------------
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
]

DESCRIPTIONS = {
    "create_lead": lambda a: (
        f"Crear un lead CRM: «{a.get('title')}»"
        f"{(' — contacto: ' + a['contact_name']) if a.get('contact_name') else ''}"
        f"{(' — email: ' + a['email']) if a.get('email') else ''}."),
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
