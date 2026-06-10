from unittest.mock import patch

import requests

from odoo.tests.common import TransactionCase

from odoo.addons.odoo_ai.ai_specs import TOOL_SPECS

PACK_BY_TOOL = {s["schema"]["function"]["name"]: s["pack"] for s in TOOL_SPECS}


class TestToolRouting(TransactionCase):
    """Selección dinámica de tools (Fase 0.2)."""

    def setUp(self):
        super().setUp()
        self.agent = self.env["odoo.ai.agent"]
        self.icp = self.env["ir.config_parameter"].sudo()
        self.conv = self.env["odoo.ai.conversation"].create({"name": "t"})

    def _packs_of(self, schemas):
        return {PACK_BY_TOOL[s["function"]["name"]] for s in schemas}

    def test_enabled_packs_param_filters(self):
        self.icp.set_param("odoo_ai.enabled_packs", "crm")
        schemas = self.agent._select_schemas(self.conv)
        self.assertEqual(self._packs_of(schemas), {"crm"})

    def test_invalid_enabled_packs_falls_back_to_all(self):
        self.icp.set_param("odoo_ai.enabled_packs", "noexiste")
        self.assertEqual(set(self.agent._enabled_packs()),
                         set(self.env["odoo.ai.tools"].list_packs()))

    def test_below_threshold_no_router_call(self):
        # Umbral alto: nunca debe llamarse al LLM para enrutar.
        self.icp.set_param("odoo_ai.router_threshold", "999")
        with patch.object(type(self.agent), "_call_llm") as mock_llm:
            schemas = self.agent._select_schemas(self.conv)
        mock_llm.assert_not_called()
        self.assertEqual(self._packs_of(schemas),
                         set(self.env["odoo.ai.tools"].list_packs()))

    def test_router_subsets_by_domain(self):
        self.icp.set_param("odoo_ai.router_threshold", "5")
        self.conv._add_message("user", content="¿cuánto stock hay de Mesa?")
        calls = []

        def fake_llm(_self, messages, tools=None):
            calls.append({"messages": messages, "tools": tools})
            return {"role": "assistant", "content": "stock"}

        with patch.object(type(self.agent), "_call_llm", fake_llm):
            schemas = self.agent._select_schemas(self.conv)
        # La llamada del router va SIN tools y el resultado solo trae stock.
        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0]["tools"])
        self.assertEqual(self._packs_of(schemas), {"stock"})

    def test_router_garbage_falls_back_to_all(self):
        self.icp.set_param("odoo_ai.router_threshold", "5")
        self.conv._add_message("user", content="hola")
        with patch.object(
            type(self.agent), "_call_llm",
            return_value={"role": "assistant", "content": "no tengo ni idea"},
        ):
            schemas = self.agent._select_schemas(self.conv)
        self.assertEqual(self._packs_of(schemas),
                         set(self.env["odoo.ai.tools"].list_packs()))

    def test_router_llm_error_falls_back_to_all(self):
        self.icp.set_param("odoo_ai.router_threshold", "5")
        self.conv._add_message("user", content="hola")
        with patch.object(
            type(self.agent), "_call_llm",
            side_effect=requests.RequestException("down"),
        ):
            schemas = self.agent._select_schemas(self.conv)
        self.assertEqual(self._packs_of(schemas),
                         set(self.env["odoo.ai.tools"].list_packs()))

    def test_get_tool_schemas_pack_filter(self):
        tools = self.env["odoo.ai.tools"]
        schemas = tools.get_tool_schemas(packs=["purchase"])
        self.assertEqual(self._packs_of(schemas), {"purchase"})
        # Sin argumento: comportamiento histórico (todas las disponibles).
        self.assertGreater(len(tools.get_tool_schemas()), len(schemas))
