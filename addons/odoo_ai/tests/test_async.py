import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase


def _assistant(content="", tool_calls=None):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


class TestAsyncMode(TransactionCase):
    """Modo asíncrono opcional (Fase 0.3) y polling de la UI."""

    def setUp(self):
        super().setUp()
        self.icp = self.env["ir.config_parameter"].sudo()
        self.conv = self.env["odoo.ai.conversation"].create({"name": "t"})

    def test_async_off_by_default(self):
        self.assertFalse(self.conv._async_on())
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(content="Hola"),
        ):
            res = self.conv.chat("hola")
        # Sin async: respuesta directa, nunca "queued".
        self.assertEqual(res["type"], "reply")

    def test_param_on_without_queue_job_stays_sync(self):
        self.icp.set_param("odoo_ai.async_enabled", "1")
        installed = self.env["ir.module.module"].sudo().search(
            [("name", "=", "queue_job"), ("state", "=", "installed")])
        if installed:
            self.skipTest("queue_job instalado en esta BD: caso cubierto en vivo")
        self.assertFalse(self.conv._async_on())
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(content="Hola"),
        ):
            res = self.conv.chat("hola")
        self.assertEqual(res["type"], "reply")

    def test_poll_updates_returns_new_messages(self):
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(content="Respuesta X"),
        ):
            self.conv.chat("hola")
        res = self.conv.poll_updates(0)
        contents = [m["content"] for m in res["messages"]]
        self.assertIn("Respuesta X", contents)
        self.assertFalse(res["thinking"])
        # Incremental: con el último id ya no devuelve nada.
        res2 = self.conv.poll_updates(res["last_message_id"])
        self.assertEqual(res2["messages"], [])

    def test_poll_updates_exposes_pending_confirmation(self):
        tc = {"id": "c1", "type": "function",
              "function": {"name": "create_lead",
                           "arguments": json.dumps({"title": "Acme"})}}
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(tool_calls=[tc]),
        ):
            self.conv.chat("crea un lead Acme")
        res = self.conv.poll_updates(0)
        self.assertTrue(res["pending"])
        self.assertEqual(res["pending"]["tool_name"], "create_lead")
        self.assertIn("Acme", res["pending"]["description"])
