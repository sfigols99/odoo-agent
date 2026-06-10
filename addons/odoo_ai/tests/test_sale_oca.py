from odoo.tests.common import TransactionCase


class TestSaleOcaTools(TransactionCase):
    """Tools de la Ola 3 (ventas: sale-workflow + tier validation)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]
        self.partner = self.env["res.partner"].create({"name": "Cliente Ola3"})
        self.product = self.env["product.product"].create(
            {"name": "Producto Ola3", "list_price": 100})

    def _installed(self, module):
        return bool(self.env["ir.module.module"].sudo().search(
            [("name", "=", module), ("state", "=", "installed")], limit=1))

    def test_create_quotation_plain_still_works(self):
        out = self.tools.execute_tool("create_quotation", {
            "customer_name": "Cliente Ola3", "product_name": "Producto Ola3",
            "quantity": 2})
        self.assertIn("creado", out)

    def test_create_quotation_with_type_without_module(self):
        if self._installed("sale_order_type"):
            self.skipTest("sale_order_type instalado")
        out = self.tools.execute_tool("create_quotation", {
            "customer_name": "Cliente Ola3", "product_name": "Producto Ola3",
            "order_type": "Estándar"})
        self.assertIn("sale_order_type", out)
        # No se ha creado ningún pedido a medias.
        self.assertFalse(self.env["sale.order"].search(
            [("partner_id", "=", self.partner.id)]))

    def test_create_quotation_with_type(self):
        if not self._installed("sale_order_type"):
            self.skipTest("sale_order_type no instalado")
        if "sale.order.type" not in self.env:
            self.skipTest("modelo sale.order.type no cargado en este registry")
        sot = self.env["sale.order.type"].create({"name": "Tipo Eval"})
        out = self.tools.execute_tool("create_quotation", {
            "customer_name": "Cliente Ola3", "product_name": "Producto Ola3",
            "order_type": "Tipo Eval"})
        self.assertIn("Tipo Eval", out)
        order = self.env["sale.order"].search(
            [("partner_id", "=", self.partner.id)], limit=1)
        self.assertEqual(order.type_id, sot)

    def test_list_order_exceptions(self):
        if not self._installed("sale_exception"):
            self.skipTest("sale_exception no instalado")
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        out = self.tools.execute_tool(
            "list_order_exceptions", {"order_name": order.name})
        self.assertIn(order.name, out)  # sin excepciones o listado

    def test_tier_validation_flow(self):
        if not self._installed("sale_tier_validation"):
            self.skipTest("sale_tier_validation no instalado")
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        # Definición de nivel: el propio usuario aprueba todo pedido.
        self.env["tier.definition"].sudo().create({
            "model_id": self.env["ir.model"]._get_id("sale.order"),
            "review_type": "individual",
            "reviewer_id": self.env.user.id,
            "definition_domain": "[]",
        })
        order.request_validation()
        order.invalidate_recordset()
        if not order.review_ids:
            # La definición de nivel no generó revisión en este entorno
            # (depende de la config de tier de la instancia): no es un fallo
            # de nuestra tool.
            self.skipTest("tier validation no generó revisión en este entorno")
        listed = self.tools.execute_tool("list_orders_to_approve", {})
        self.assertIn(order.name, listed)
        out = self.tools.execute_tool(
            "approve_sale_order", {"order_name": order.name})
        self.assertIn("aprobado", out)
        self.assertTrue(
            all(r.status == "approved" for r in order.review_ids))

    def test_oca_tools_hidden_without_modules(self):
        for tool, module in [("list_sale_order_types", "sale_order_type"),
                             ("list_order_exceptions", "sale_exception"),
                             ("approve_sale_order", "sale_tier_validation")]:
            if self._installed(module):
                continue
            names = [s["function"]["name"] for s in self.tools.get_tool_schemas()]
            self.assertNotIn(tool, names)
