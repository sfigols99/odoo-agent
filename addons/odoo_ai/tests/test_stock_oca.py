from odoo.tests.common import TransactionCase


class TestStockTools(TransactionCase):
    """Tools de la Ola 4 (almacén: core pickings + OCA stock_inventory)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]

    def _installed(self, module):
        return bool(self.env["ir.module.module"].sudo().search(
            [("name", "=", module), ("state", "=", "installed")], limit=1))

    def test_list_pending_pickings_empty_or_list(self):
        out = self.tools.execute_tool("list_pending_pickings", {})
        self.assertTrue(out)  # texto siempre, nunca excepción

    def test_validate_picking_not_found(self):
        out = self.tools.execute_tool(
            "validate_picking", {"picking_name": "NO/EXISTE/999"})
        self.assertIn("No se encontró", out)

    def test_validate_picking_flow(self):
        # Transferencia interna mínima con stock disponible.
        product = self.env["product.product"].create(
            {"name": "Stock Ola4", "is_storable": True})
        wh = self.env["stock.warehouse"].search([], limit=1)
        loc = wh.lot_stock_id
        self.env["stock.quant"].with_context(inventory_mode=True).create({
            "product_id": product.id, "location_id": loc.id,
            "inventory_quantity": 10}).action_apply_inventory()
        pick = self.env["stock.picking"].create({
            "picking_type_id": wh.int_type_id.id,
            "location_id": loc.id,
            "location_dest_id": loc.id,
            "move_ids": [(0, 0, {
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": 2,
                "product_uom": product.uom_id.id,
                "location_id": loc.id,
                "location_dest_id": loc.id,
            })],
        })
        pick.action_confirm()
        pick.action_assign()
        out = self.tools.execute_tool(
            "validate_picking", {"picking_name": pick.name})
        self.assertIn(pick.name, out)

    def test_check_stock_shows_unreserved_with_module(self):
        if not self._installed("stock_available_unreserved"):
            self.skipTest("stock_available_unreserved no instalado")
        self.env["product.product"].create(
            {"name": "Unres Ola4", "is_storable": True})
        out = self.tools.execute_tool("check_stock", {"product_name": "Unres Ola4"})
        self.assertIn("sin reservar", out)

    def test_inventory_adjustment_flow(self):
        if not self._installed("stock_inventory"):
            self.skipTest("stock_inventory no instalado")
        self.env["product.product"].create(
            {"name": "Conteo Ola4", "is_storable": True})
        out = self.tools.execute_tool(
            "start_inventory_adjustment", {"product_name": "Conteo Ola4"})
        self.assertIn("iniciado", out)
        inv = self.env["stock.inventory"].search(
            [("name", "ilike", "Conteo Ola4")], limit=1)
        self.assertEqual(inv.state, "in_progress")
        listed = self.tools.execute_tool("list_inventory_adjustments", {})
        self.assertIn(inv.name, listed)

    def test_inventory_tools_hidden_without_module(self):
        if self._installed("stock_inventory"):
            self.skipTest("stock_inventory instalado")
        names = [s["function"]["name"] for s in self.tools.get_tool_schemas()]
        self.assertNotIn("start_inventory_adjustment", names)
