from odoo.tests.common import TransactionCase


class TestAccountTools(TransactionCase):
    """Tools de la Ola 6 (finanzas: vencimientos core + remesas OCA)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]

    def _installed(self, module):
        return bool(self.env["ir.module.module"].sudo().search(
            [("name", "=", module), ("state", "=", "installed")], limit=1))

    def test_upcoming_due_dates_text(self):
        # Sin datos contables: mensaje "no hay"; con datos: listado. Nunca
        # excepción.
        out = self.tools.execute_tool("list_upcoming_due_dates", {"days": 7})
        self.assertTrue(out)
        self.assertNotIn("Error", out)

    def test_upcoming_due_dates_with_invoice(self):
        partner = self.env["res.partner"].create({"name": "Deudor Ola6"})
        product = self.env["product.product"].create(
            {"name": "Servicio Ola6", "list_price": 100})
        inv = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_date_due": "2020-01-01",  # vencida seguro
            "invoice_line_ids": [(0, 0, {
                "product_id": product.id, "quantity": 1, "price_unit": 100})],
        })
        inv.action_post()
        out = self.tools.execute_tool("list_upcoming_due_dates", {"days": 7})
        self.assertIn("Deudor Ola6", out)
        self.assertIn("VENCIDO", out)
        self.assertIn("A COBRAR", out)

    def test_payment_order_tools(self):
        if not self._installed("account_payment_order"):
            self.skipTest("account_payment_order no instalado")
        # Listado nunca lanza (texto siempre).
        out = self.tools.execute_tool("list_payment_orders", {})
        self.assertTrue(out)
        # Confirmar una orden inexistente.
        out = self.tools.execute_tool(
            "confirm_payment_order", {"order_name": "NOEXISTE"})
        self.assertIn("No se encontró", out)

    def test_payment_order_hidden_without_module(self):
        if self._installed("account_payment_order"):
            self.skipTest("account_payment_order instalado")
        names = [s["function"]["name"] for s in self.tools.get_tool_schemas()]
        self.assertNotIn("confirm_payment_order", names)
