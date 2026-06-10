from odoo.tests.common import TransactionCase


class TestContractKpiTools(TransactionCase):
    """Tools de la Ola 8 (contratos recurrentes + KPIs MIS Builder)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]

    def _installed(self, module):
        return bool(self.env["ir.module.module"].sudo().search(
            [("name", "=", module), ("state", "=", "installed")], limit=1))

    def test_contract_listing_and_guards(self):
        if not self._installed("contract"):
            self.skipTest("contract no instalado")
        partner = self.env["res.partner"].create({"name": "Abonado Ola8"})
        contract = self.env["contract.contract"].create({
            "name": "Mantenimiento Ola8", "partner_id": partner.id})
        out = self.tools.execute_tool("list_active_contracts", {})
        self.assertIn("Mantenimiento Ola8", out)
        # Sin líneas recurrentes: no hay próxima factura y la tool lo dice.
        out = self.tools.execute_tool(
            "generate_contract_invoice",
            {"contract_name": "Mantenimiento Ola8"})
        self.assertIn("no tiene próxima fecha", out)
        self.assertTrue(contract)

    def test_contracts_to_renew(self):
        if not self._installed("contract"):
            self.skipTest("contract no instalado")
        partner = self.env["res.partner"].create({"name": "Renueva Ola8"})
        self.env["contract.contract"].create({
            "name": "Caduca Ola8", "partner_id": partner.id,
            "date_end": "2020-01-01"})
        out = self.tools.execute_tool("list_contracts_to_renew", {"days": 30})
        self.assertIn("Caduca Ola8", out)

    def test_kpi_tools(self):
        if not self._installed("mis_builder"):
            self.skipTest("mis_builder no instalado")
        out = self.tools.execute_tool("list_kpi_reports", {})
        self.assertTrue(out)  # listado o "no hay informes"
        out = self.tools.execute_tool("get_kpi_report", {"name": "NOEXISTE"})
        self.assertIn("No se encontró", out)

    def test_hidden_without_modules(self):
        names = [s["function"]["name"] for s in self.tools.get_tool_schemas()]
        if not self._installed("contract"):
            self.assertNotIn("generate_contract_invoice", names)
        if not self._installed("mis_builder"):
            self.assertNotIn("get_kpi_report", names)
