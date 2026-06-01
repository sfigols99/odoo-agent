import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase


def _assistant(content="", tool_calls=None):
    """Construye un mensaje 'assistant' como el que devuelve vLLM."""
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def _tool_call(call_id, name, arguments):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


class TestAgentLoop(TransactionCase):
    def setUp(self):
        super().setUp()
        self.conv = self.env["odoo.ai.conversation"].create({"name": "test"})

    def test_plain_reply_is_persisted(self):
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(content="Hola"),
        ):
            res = self.conv.chat("¿qué tal?")
        self.assertEqual(res["type"], "reply")
        self.assertEqual(res["content"], "Hola")
        roles = self.conv.message_ids.mapped("role")
        self.assertEqual(roles, ["user", "assistant"])

    def test_write_tool_pauses_for_confirmation(self):
        # El modelo propone una escritura: el bucle NO la ejecuta, pide confirmar.
        tc = _tool_call("c1", "create_lead", {"title": "Acme"})
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(tool_calls=[tc]),
        ):
            res = self.conv.chat("crea un lead Acme")
        self.assertEqual(res["type"], "confirm")
        self.assertEqual(res["tool_name"], "create_lead")
        self.assertTrue(self.conv.pending_tool_calls)
        # No se ha creado ningún lead todavía.
        self.assertFalse(self.env["crm.lead"].search([("name", "=", "Acme")]))
        # El mensaje 'assistant' con tool_calls se persiste ANTES de la respuesta
        # 'tool' (invariante del formato OpenAI).
        last = self.conv.message_ids[-1]
        self.assertEqual(last.role, "assistant")
        self.assertTrue(last.tool_calls)

    def test_confirm_executes_write(self):
        tc = _tool_call("c1", "create_lead", {"title": "Acme"})
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(tool_calls=[tc]),
        ):
            self.conv.chat("crea un lead Acme")
        # Al confirmar, se ejecuta la tool y el siguiente _run devuelve la respuesta.
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(content="Lead creado."),
        ):
            res = self.conv.execute_pending(True)
        self.assertEqual(res["type"], "reply")
        self.assertTrue(self.env["crm.lead"].search([("name", "=", "Acme")]))
        self.assertFalse(self.conv.pending_tool_calls)

    def test_cancel_does_not_execute_write(self):
        tc = _tool_call("c1", "create_lead", {"title": "Fantasma"})
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(tool_calls=[tc]),
        ):
            self.conv.chat("crea un lead Fantasma")
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            return_value=_assistant(content="Cancelado."),
        ):
            res = self.conv.execute_pending(False)
        self.assertEqual(res["type"], "reply")
        self.assertFalse(self.env["crm.lead"].search([("name", "=", "Fantasma")]))
        # Existe una respuesta 'tool' para el tool_call cancelado: el historial
        # no queda con un tool_call_id colgando.
        tool_msgs = self.conv.message_ids.filtered(lambda m: m.role == "tool")
        self.assertTrue(tool_msgs)
        self.assertEqual(tool_msgs[-1].tool_call_id, "c1")

    def test_malformed_llm_response_is_handled(self):
        # _call_llm lanza RequestException ante un cuerpo inesperado; el bucle
        # lo traduce a una respuesta amable en vez de un 500.
        import requests
        with patch.object(
            type(self.env["odoo.ai.agent"]), "_call_llm",
            side_effect=requests.RequestException("boom"),
        ):
            res = self.conv.chat("hola")
        self.assertEqual(res["type"], "reply")
        self.assertIn("error", res)
