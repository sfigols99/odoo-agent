from odoo.tests.common import TransactionCase

from odoo.addons.odoo_ai.ai_specs import (
    DESCRIPTIONS,
    PACK_NAMES,
    TOOL_SPECS,
)


class TestToolPacks(TransactionCase):
    """Integridad de la agregación de packs (Fase 0.1)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]

    def test_every_spec_has_valid_pack(self):
        for spec in TOOL_SPECS:
            self.assertIn(spec.get("pack"), PACK_NAMES,
                          f"spec sin pack válido: {spec['schema']['function']['name']}")

    def test_every_method_resolves_on_model(self):
        # Si un mixin no se carga (olvido en models/__init__.py), el método
        # no existe y la tool fallaría en runtime: lo detectamos aquí.
        for spec in TOOL_SPECS:
            self.assertTrue(
                hasattr(self.tools, spec["method"]),
                f"método {spec['method']} no resuelto en odoo.ai.tools "
                f"(¿mixin del pack '{spec['pack']}' no importado?)")

    def test_every_write_tool_has_confirmation_description(self):
        for spec in TOOL_SPECS:
            if spec["is_write"]:
                name = spec["schema"]["function"]["name"]
                self.assertIn(name, DESCRIPTIONS,
                              f"falta descripción de confirmación para {name}")

    def test_list_packs_returns_available(self):
        packs = self.tools.list_packs()
        # Todos los packs core están disponibles en una instalación completa.
        for p in PACK_NAMES:
            self.assertIn(p, packs)
            self.assertTrue(packs[p])  # con descripción no vacía

    def test_registry_reexports_for_compat(self):
        # Los imports históricos desde models.ai_tools siguen funcionando.
        from odoo.addons.odoo_ai.models.ai_tools import (
            DESCRIPTIONS as D2,
            TOOL_SPECS as T2,
        )
        self.assertIs(D2, DESCRIPTIONS)
        self.assertIs(T2, TOOL_SPECS)
