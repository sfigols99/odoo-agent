from odoo import fields, models


class AiConversation(models.Model):
    _name = "odoo.ai.conversation"
    _description = "Conversación con el Asistente IA"
    _order = "id desc"

    name = fields.Char(default="Nueva conversación")
    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        required=True,
        index=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
    )
    message_ids = fields.One2many(
        "odoo.ai.message", "conversation_id", string="Mensajes"
    )
    # Tool-calls de ESCRITURA pendientes de confirmación del usuario (JSON).
    # Mientras no esté vacío, la UI muestra la tarjeta Confirmar/Cancelar.
    pending_tool_calls = fields.Text()

    # ---- Entrada RPC desde el frontend OWL (orm.call) ----
    def chat(self, user_message):
        """Envía un mensaje del usuario y devuelve la respuesta del agente."""
        self.ensure_one()
        return self.env["odoo.ai.agent"].run_chat(self, user_message)

    def execute_pending(self, confirm):
        """Confirma (True) o cancela (False) la acción de escritura pendiente."""
        self.ensure_one()
        return self.env["odoo.ai.agent"].run_execute(self, confirm)

    def _add_message(self, role, content=None, tool_calls=None,
                     tool_call_id=None, name=None):
        """Persiste un mensaje en la conversación (historial + auditoría)."""
        self.ensure_one()
        return self.env["odoo.ai.message"].create({
            "conversation_id": self.id,
            "role": role,
            "content": content or "",
            "tool_calls": tool_calls or False,
            "tool_call_id": tool_call_id or False,
            "name": name or False,
        })
