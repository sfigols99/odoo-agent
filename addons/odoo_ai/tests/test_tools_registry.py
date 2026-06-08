from odoo.tests.common import TransactionCase


class TestToolsRegistry(TransactionCase):
    """Capa de despacho/registro de herramientas (lógica pura, sin LLM)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]

    def test_schemas_match_specs(self):
        schemas = self.tools.get_tool_schemas()
        names = [s["function"]["name"] for s in schemas]
        # Cada schema está bien formado y los nombres son únicos.
        self.assertEqual(len(names), len(set(names)), "nombres de tool duplicados")
        for s in schemas:
            self.assertEqual(s["type"], "function")
            self.assertIn("parameters", s["function"])

    def test_is_write_tool_classification(self):
        self.assertTrue(self.tools.is_write_tool("create_lead"))
        self.assertTrue(self.tools.is_write_tool("confirm_purchase_order"))
        self.assertFalse(self.tools.is_write_tool("check_stock"))
        self.assertFalse(self.tools.is_write_tool("list_open_opportunities"))
        # Una tool inexistente no se considera escritura.
        self.assertFalse(self.tools.is_write_tool("does_not_exist"))

    def test_describe_action_known_and_unknown(self):
        desc = self.tools.describe_action("create_lead", {"title": "Acme"})
        self.assertIn("Acme", desc)
        # Sin formateador específico, hay un fallback legible.
        fallback = self.tools.describe_action("check_stock", {"product_name": "Mesa"})
        self.assertIn("check_stock", fallback)

    def test_execute_unknown_tool_returns_error_text(self):
        # execute_tool nunca lanza: devuelve texto que el modelo puede leer.
        out = self.tools.execute_tool("nope", {})
        self.assertIn("desconocida", out)
