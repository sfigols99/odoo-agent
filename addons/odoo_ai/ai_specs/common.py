# Helpers de schemas — módulo PURO (sin imports de Odoo), para que los specs
# puedan importarse también fuera de Odoo (p. ej. el harness de evals).


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
