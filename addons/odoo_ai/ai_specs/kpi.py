from .common import _fn

PACK = "kpi"
PACK_DESCRIPTION = ("Indicadores/KPIs: consultar los informes MIS Builder "
                    "configurados y leer sus valores.")

# Requieren OCA `mis_builder` (informes KPI configurables, alternativa
# gratuita a los dashboards de Enterprise).
SPECS = [
    {"is_write": False, "requires": ["mis_builder"], "method": "_list_kpi_reports",
     "schema": _fn(
        "list_kpi_reports",
        "Lista los informes KPI (MIS Builder) disponibles.",
        {})},
    {"is_write": False, "requires": ["mis_builder"], "method": "_get_kpi_report",
     "schema": _fn(
        "get_kpi_report",
        "Calcula un informe KPI (MIS Builder) por nombre y devuelve sus "
        "valores por periodo.",
        {"name": {"type": "string", "description": "Nombre del informe KPI."}},
        ["name"])},
]

DESCRIPTIONS = {}
