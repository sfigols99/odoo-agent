from odoo.tests.common import TransactionCase


class TestPurchaseOcaTools(TransactionCase):
    """Tools de la Ola 5 (compras: purchase_request + purchase_order_type)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]
        self.product = self.env["product.product"].create(
            {"name": "Tornillo Ola5", "purchase_ok": True})

    def _installed(self, module):
        return bool(self.env["ir.module.module"].sudo().search(
            [("name", "=", module), ("state", "=", "installed")], limit=1))

    def test_purchase_request_flow(self):
        if not self._installed("purchase_request"):
            self.skipTest("purchase_request no instalado")
        out = self.tools.execute_tool("create_purchase_request", {
            "product_name": "Tornillo Ola5", "quantity": 10,
            "reason": "Reposición taller"})
        self.assertIn("enviada a", out)
        req = self.env["purchase.request"].search(
            [("line_ids.product_id", "=", self.product.id)], limit=1)
        self.assertEqual(req.state, "to_approve")
        listed = self.tools.execute_tool("list_purchase_requests", {})
        self.assertIn(req.name, listed)
        approved = self.tools.execute_tool(
            "approve_purchase_request", {"request_name": req.name})
        self.assertIn("aprobada", approved)
        self.assertEqual(req.state, "approved")

    def test_approve_request_wrong_state(self):
        if not self._installed("purchase_request"):
            self.skipTest("purchase_request no instalado")
        req = self.env["purchase.request"].create({
            "line_ids": [(0, 0, {"product_id": self.product.id,
                                 "product_qty": 1,
                                 "name": "x"})]})
        out = self.tools.execute_tool(
            "approve_purchase_request", {"request_name": req.name})
        self.assertIn("no está pendiente", out)

    def test_create_po_with_type_without_module(self):
        if self._installed("purchase_order_type"):
            self.skipTest("purchase_order_type instalado")
        vendor = self.env["res.partner"].create({"name": "Proveedor Ola5"})
        out = self.tools.execute_tool("create_purchase_order", {
            "vendor_name": "Proveedor Ola5", "product_name": "Tornillo Ola5",
            "order_type": "Normal"})
        self.assertIn("purchase_order_type", out)
        self.assertFalse(self.env["purchase.order"].search(
            [("partner_id", "=", vendor.id)]))

    def test_create_po_with_type(self):
        if not self._installed("purchase_order_type"):
            self.skipTest("purchase_order_type no instalado")
        self.env["res.partner"].create({"name": "Proveedor Ola5"})
        pot = self.env["purchase.order.type"].search([], limit=1)
        if not pot:
            pot = self.env["purchase.order.type"].create({"name": "Tipo Ola5"})
        out = self.tools.execute_tool("create_purchase_order", {
            "vendor_name": "Proveedor Ola5", "product_name": "Tornillo Ola5",
            "order_type": pot.name})
        self.assertIn(pot.name, out)

    def test_request_tools_hidden_without_module(self):
        if self._installed("purchase_request"):
            self.skipTest("purchase_request instalado")
        names = [s["function"]["name"] for s in self.tools.get_tool_schemas()]
        self.assertNotIn("create_purchase_request", names)
