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

    # ---------------- Registro condicional ----------------
    def test_crm_tools_exposed_when_crm_installed(self):
        # crm es dependencia del addon: estas tools deben estar expuestas.
        names = [s["function"]["name"] for s in self.tools.get_tool_schemas()]
        for expected in ("set_opportunity_stage", "mark_opportunity_won",
                         "schedule_activity", "list_stale_opportunities"):
            self.assertIn(expected, names)

    def test_tool_with_unmet_requires_is_hidden_and_blocked(self):
        # Una tool que requiere un módulo no instalado no se expone ni se ejecuta.
        installed = self.tools._installed_modules()
        self.assertNotIn("modulo_oca_inexistente", installed)
        fake_spec = {"requires": ["modulo_oca_inexistente"]}
        self.assertFalse(self.tools._is_available(fake_spec, installed))
        # Y una tool core (sin requires) siempre disponible.
        self.assertTrue(self.tools._is_available({}, installed))

    def test_describe_action_covers_crm_writes(self):
        # Toda tool de escritura debería tener una descripción específica para
        # la tarjeta de confirmación (no solo el fallback genérico).
        from odoo.addons.odoo_ai.models.ai_tools import DESCRIPTIONS, TOOL_SPECS
        for spec in TOOL_SPECS:
            if spec["is_write"]:
                name = spec["schema"]["function"]["name"]
                self.assertIn(name, DESCRIPTIONS,
                              f"falta descripción de confirmación para {name}")
