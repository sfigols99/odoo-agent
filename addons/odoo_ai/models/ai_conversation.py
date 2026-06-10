import json

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
    # Fase 0.3: True mientras un job asíncrono está procesando el turno.
    is_thinking = fields.Boolean(default=False)

    # ---- Entrada RPC desde el frontend OWL (orm.call) ----
    def chat(self, user_message):
        """Envía un mensaje del usuario y devuelve la respuesta del agente.

        En modo síncrono (por defecto) bloquea hasta tener respuesta. Con
        `odoo_ai.async_enabled=1` y queue_job instalado, encola el turno y
        devuelve {"type": "queued"}; la UI hace polling con poll_updates().
        """
        self.ensure_one()
        agent = self.env["odoo.ai.agent"]
        if not self._async_on():
            return agent.run_chat(self, user_message)
        agent._cancel_pending(self)
        msg = self._add_message("user", content=user_message or "")
        self.is_thinking = True
        self.with_delay(description="odoo_ai: turno de chat")._job_run_chat()
        return {"type": "queued", "last_message_id": msg.id}

    def execute_pending(self, confirm):
        """Confirma (True) o cancela (False) la acción de escritura pendiente."""
        self.ensure_one()
        agent = self.env["odoo.ai.agent"]
        if not self._async_on():
            return agent.run_execute(self, confirm)
        last = self.message_ids[-1].id if self.message_ids else 0
        self.is_thinking = True
        self.with_delay(description="odoo_ai: confirmación")._job_run_execute(
            bool(confirm))
        return {"type": "queued", "last_message_id": last}

    def poll_updates(self, last_message_id=0):
        """Estado incremental para la UI en modo asíncrono.

        Devuelve los mensajes 'assistant' con contenido posteriores a
        `last_message_id`, la acción pendiente de confirmación (si la hay y el
        job ya terminó) y si el turno sigue en proceso.
        """
        self.ensure_one()
        msgs = self.message_ids.filtered(
            lambda m: m.id > (last_message_id or 0)
            and m.role == "assistant" and (m.content or "").strip())
        pending = json.loads(self.pending_tool_calls or "[]")
        payload = None
        if pending and not self.is_thinking:
            payload = self.env["odoo.ai.agent"]._confirm_payload(pending[0])
        return {
            "messages": [{"id": m.id, "content": m.content} for m in msgs],
            "pending": payload,
            "thinking": self.is_thinking,
            "last_message_id": msgs[-1].id if msgs else (last_message_id or 0),
        }

    # ---- Modo asíncrono (Fase 0.3, opcional) ----
    def _async_on(self):
        """Asíncrono solo si: parámetro activo + queue_job instalado."""
        icp = self.env["ir.config_parameter"].sudo()
        flag = (icp.get_param("odoo_ai.async_enabled", "0") or "0").lower()
        if flag not in ("1", "true", "yes", "on"):
            return False
        if not hasattr(self, "with_delay"):
            return False
        return bool(self.env["ir.module.module"].sudo().search(
            [("name", "=", "queue_job"), ("state", "=", "installed")], limit=1))

    def _job_run_chat(self):
        """Cuerpo del job: ejecuta el bucle del agente (mensaje ya añadido)."""
        try:
            self.env["odoo.ai.agent"]._run(self)
        finally:
            self.is_thinking = False

    def _job_run_execute(self, confirm):
        try:
            self.env["odoo.ai.agent"].run_execute(self, confirm)
        finally:
            self.is_thinking = False

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
