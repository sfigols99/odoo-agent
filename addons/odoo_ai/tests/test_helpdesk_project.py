from odoo.tests.common import TransactionCase


class TestHelpdeskProjectTools(TransactionCase):
    """Tools de la Ola 7 (helpdesk OCA + proyectos core condicional)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]

    def _installed(self, module):
        return bool(self.env["ir.module.module"].sudo().search(
            [("name", "=", module), ("state", "=", "installed")], limit=1))

    # ---------------- helpdesk_mgmt ----------------
    def test_ticket_full_flow(self):
        if not self._installed("helpdesk_mgmt"):
            self.skipTest("helpdesk_mgmt no instalado")
        out = self.tools.execute_tool("create_ticket", {
            "title": "Portal caído", "description": "El cliente no puede entrar"})
        self.assertIn("creado", out)
        ticket = self.env["helpdesk.ticket"].search(
            [("name", "=", "Portal caído")], limit=1)
        self.assertTrue(ticket.number and ticket.number != "/")
        listed = self.tools.execute_tool("list_open_tickets", {})
        self.assertIn(ticket.number, listed)
        detail = self.tools.execute_tool("get_ticket", {"number": ticket.number})
        self.assertIn("Portal caído", detail)
        assigned = self.tools.execute_tool("assign_ticket", {
            "number": ticket.number, "user": self.env.user.name})
        self.assertIn(self.env.user.name, assigned)
        closed = self.tools.execute_tool("close_ticket", {
            "number": ticket.number, "note": "Resuelto"})
        # Cierra o avisa de que no hay etapa de cierre configurada.
        self.assertTrue("cerrado" in closed or "etapa de cierre" in closed)

    def test_close_already_closed(self):
        if not self._installed("helpdesk_mgmt"):
            self.skipTest("helpdesk_mgmt no instalado")
        stage = self.env["helpdesk.ticket.stage"].search(
            [("closed", "=", True)], limit=1)
        if not stage:
            self.skipTest("sin etapa de cierre en datos de demo")
        ticket = self.env["helpdesk.ticket"].create({
            "name": "Ya cerrado", "description": "<p>x</p>",
            "stage_id": stage.id})
        out = self.tools.execute_tool("close_ticket", {"number": ticket.number})
        self.assertIn("ya está cerrado", out)

    # ---------------- project (core, condicional) ----------------
    def test_task_flow(self):
        if not self._installed("project"):
            self.skipTest("project no instalado")
        self.env["project.project"].create({"name": "Proyecto Ola7"})
        out = self.tools.execute_tool("create_task", {
            "project_name": "Proyecto Ola7", "title": "Revisar formulario",
            "assignee": self.env.user.name})
        self.assertIn("Revisar formulario", out)
        listed = self.tools.execute_tool("list_my_tasks", {})
        self.assertIn("Revisar formulario", listed)

    def test_task_unknown_project_lists_available(self):
        if not self._installed("project"):
            self.skipTest("project no instalado")
        out = self.tools.execute_tool("create_task", {
            "project_name": "Inexistente XYZ", "title": "x"})
        self.assertIn("No se encontró el proyecto", out)

    def test_hidden_without_modules(self):
        names = [s["function"]["name"] for s in self.tools.get_tool_schemas()]
        if not self._installed("helpdesk_mgmt"):
            self.assertNotIn("create_ticket", names)
        if not self._installed("project"):
            self.assertNotIn("create_task", names)
