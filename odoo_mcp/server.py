import os
import xmlrpc.client

from mcp.server.fastmcp import FastMCP

# Transporte HTTP para desplegar como servicio de red en K8s (host/port).
mcp = FastMCP("Odoo Enterprise Server", host="0.0.0.0", port=8000)

ODOO_URL = os.getenv("ODOO_URL", "http://odoo-service:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
# Usuario de BAJO PRIVILEGIO (no admin) + API key como contraseña. Ver Fase 7.
ODOO_USER = os.getenv("ODOO_USER", "ai_integration")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")


def _get_odoo_connection():
    """Conexión a la API XML-RPC de Odoo (autenticación con API key)."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise RuntimeError(
            "Autenticación con Odoo fallida: revisa ODOO_USER / ODOO_PASSWORD / ODOO_DB."
        )
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models


@mcp.tool()
def consultar_estoc_producte(nom_producte: str) -> str:
    """Consulta l'estoc físic disponible d'un producte a Odoo pel seu nom."""
    try:
        uid, models = _get_odoo_connection()
        product_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "product.product", "search",
            [[["name", "ilike", nom_producte]]],
            {"limit": 1},
        )
        if not product_ids:
            return f"No s'ha trobat cap producte amb el nom '{nom_producte}'."
        product_data = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "product.product", "read",
            [product_ids],
            {"fields": ["display_name", "qty_available"]},
        )
        prod = product_data[0]
        return (f"Producte: {prod['display_name']} | "
                f"Estoc disponible: {prod['qty_available']} unitats.")
    except Exception as e:
        return f"Error al connectar amb Odoo: {str(e)}"


@mcp.tool()
def crear_lead_crm(titol: str, nom_client: str, email: str,
                   descripcio: str = "") -> str:
    """Crea una nova oportunitat o lead al mòdul CRM d'Odoo."""
    try:
        uid, models = _get_odoo_connection()
        lead_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "crm.lead", "create",
            [{
                "name": titol,
                "contact_name": nom_client,
                "email_from": email,
                "description": descripcio,
                "type": "lead",
            }],
        )
        return f"Lead creat correctament amb l'ID: {lead_id}."
    except Exception as e:
        return f"Error en crear el lead: {str(e)}"


if __name__ == "__main__":
    # Sirve MCP en http://<host>:8000/mcp para clientes externos (Claude Desktop, etc.)
    mcp.run(transport="streamable-http")
