from odoo import fields, models


class AiMessage(models.Model):
    _name = "odoo.ai.message"
    _description = "Mensaje del Asistente IA"
    _order = "id asc"

    conversation_id = fields.Many2one(
        "odoo.ai.conversation",
        required=True,
        index=True,
        ondelete="cascade",
    )
    role = fields.Selection(
        [
            ("system", "System"),
            ("user", "User"),
            ("assistant", "Assistant"),
            ("tool", "Tool"),
        ],
        required=True,
    )
    content = fields.Text()
    # Para mensajes 'assistant': JSON con la lista de tool_calls solicitados.
    tool_calls = fields.Text(string="Tool calls (JSON)")
    # Para mensajes 'tool': id de la tool_call respondida y nombre de la tool.
    tool_call_id = fields.Char()
    name = fields.Char(string="Nombre de la herramienta")
