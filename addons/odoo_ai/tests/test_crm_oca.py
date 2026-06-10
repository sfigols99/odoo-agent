from odoo.tests.common import TransactionCase


class TestCrmOcaTools(TransactionCase):
    """Tools de la Ola 2 (extensiones OCA de CRM, registro condicional).

    Cada test se salta si su módulo OCA no está instalado en la BD de test;
    la CI instala todos (ver .github/workflows/ci.yml).
    """

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]
        self.opp = self.env["crm.lead"].create({
            "name": "OCA Test Opp", "type": "opportunity"})

    def _installed(self, module):
        return bool(self.env["ir.module.module"].sudo().search(
            [("name", "=", module), ("state", "=", "installed")], limit=1))

    def test_hidden_and_blocked_without_modules(self):
        for tool, module in [("find_lead_by_code", "crm_lead_code"),
                             ("add_product_interest", "crm_lead_product"),
                             ("log_phonecall", "crm_phonecall")]:
            if self._installed(module):
                continue
            names = [s["function"]["name"] for s in self.tools.get_tool_schemas()]
            self.assertNotIn(tool, names)
            self.assertIn("no está disponible", self.tools.execute_tool(tool, {}))

    def test_find_lead_by_code(self):
        if not self._installed("crm_lead_code"):
            self.skipTest("crm_lead_code no instalado")
        self.assertTrue(self.opp.code)
        out = self.tools.execute_tool("find_lead_by_code", {"code": self.opp.code})
        self.assertIn("OCA Test Opp", out)
        self.assertIn(self.opp.code, out)

    def test_add_and_list_product_interest(self):
        if not self._installed("crm_lead_product"):
            self.skipTest("crm_lead_product no instalado")
        product = self.env["product.product"].create(
            {"name": "Widget OCA", "list_price": 10})
        out = self.tools.execute_tool("add_product_interest", {
            "name": "OCA Test Opp", "product_name": "Widget OCA",
            "quantity": 3})
        self.assertIn("Widget OCA", out)
        self.assertEqual(len(self.opp.lead_line_ids), 1)
        self.assertEqual(self.opp.lead_line_ids.product_qty, 3)
        self.assertEqual(self.opp.lead_line_ids.product_id, product)
        listed = self.tools.execute_tool(
            "list_product_interests", {"name": "OCA Test Opp"})
        self.assertIn("Widget OCA", listed)

    def test_log_and_list_phonecalls(self):
        if not self._installed("crm_phonecall"):
            self.skipTest("crm_phonecall no instalado")
        out = self.tools.execute_tool("log_phonecall", {
            "name": "OCA Test Opp", "summary": "Llamada de prueba",
            "duration_minutes": 15, "direction": "out"})
        self.assertIn("Llamada registrada", out)
        call = self.env["crm.phonecall"].search(
            [("opportunity_id", "=", self.opp.id)], limit=1)
        self.assertTrue(call)
        self.assertEqual(call.state, "done")
        self.assertEqual(call.duration, 15)
        listed = self.tools.execute_tool("list_phonecalls", {})
        self.assertIn("Llamada de prueba", listed)

    def test_get_opportunity_shows_code_if_module(self):
        if not self._installed("crm_lead_code"):
            self.skipTest("crm_lead_code no instalado")
        out = self.tools.execute_tool("get_opportunity", {"name": "OCA Test Opp"})
        self.assertIn(self.opp.code, out)
