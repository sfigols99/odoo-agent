{
    "name": "Odoo AI Assistant",
    "summary": "Asistente de IA embebido en Odoo (stock, CRM/ventas, "
               "facturación y compras) con modelo local vía vLLM.",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "category": "Productivity",
    "author": "odoo-agent",
    "website": "https://github.com/",
    # Los 4 dominios + web para la UI OWL del chat.
    "depends": [
        "base",
        "web",
        "product",
        "stock",
        "crm",
        "sale_management",
        "account",
        "purchase",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ai_security.xml",
        "data/ai_config_params.xml",
        "views/ai_client_action.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_ai/static/src/scss/ai_chat.scss",
            "odoo_ai/static/src/js/ai_chat_action.js",
            "odoo_ai/static/src/xml/ai_chat_action.xml",
        ],
    },
    "application": True,
    "installable": True,
}
