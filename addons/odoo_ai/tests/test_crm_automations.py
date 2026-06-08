from odoo.tests.common import TransactionCase


class TestCrmAutomations(TransactionCase):
    """Tools de automatización de CRM (ejecutadas sobre el ORM real)."""

    def setUp(self):
        super().setUp()
        self.tools = self.env["odoo.ai.tools"]
        self.opp = self.env["crm.lead"].create({
            "name": "Oportunidad Test Alfa",
            "type": "opportunity",
            "contact_name": "Joan Test",
            "email_from": "joan@test.example",
        })

    def test_get_opportunity(self):
        out = self.tools.execute_tool("get_opportunity", {"name": "Test Alfa"})
        self.assertIn("Oportunidad Test Alfa", out)
        self.assertIn("Etapa:", out)

    def test_find_lead_ambiguous(self):
        self.env["crm.lead"].create({
            "name": "Oportunidad Test Beta", "type": "opportunity"})
        # "Oportunidad Test" coincide con dos => mensaje de ambigüedad.
        out = self.tools.execute_tool("get_opportunity", {"name": "Oportunidad Test"})
        self.assertIn("varias coincidencias", out)

    def test_set_stage(self):
        stage = self.env["crm.stage"].search([], limit=1)
        out = self.tools.execute_tool(
            "set_opportunity_stage",
            {"name": "Test Alfa", "stage_name": stage.name})
        self.assertEqual(self.opp.stage_id, stage)
        self.assertIn(stage.name, out)

    def test_mark_won(self):
        self.tools.execute_tool("mark_opportunity_won", {"name": "Test Alfa"})
        self.assertEqual(self.opp.probability, 100.0)

    def test_mark_lost_with_reason(self):
        self.tools.execute_tool(
            "mark_opportunity_lost",
            {"name": "Test Alfa", "reason": "Precio demasiado alto"})
        self.assertFalse(self.opp.active)

    def test_assign(self):
        out = self.tools.execute_tool(
            "assign_opportunity",
            {"name": "Test Alfa", "salesperson": self.env.user.name})
        self.assertEqual(self.opp.user_id, self.env.user)
        self.assertIn(self.env.user.name, out)

    def test_schedule_activity(self):
        before = len(self.opp.activity_ids)
        self.tools.execute_tool("schedule_activity", {
            "name": "Test Alfa", "summary": "Llamar al cliente",
            "activity_type": "call", "due_in_days": 2})
        self.assertEqual(len(self.opp.activity_ids), before + 1)
        self.assertEqual(self.opp.activity_ids[-1].summary, "Llamar al cliente")

    def test_log_note(self):
        before = len(self.opp.message_ids)
        self.tools.execute_tool(
            "log_note", {"name": "Test Alfa", "note": "Cliente interesado"})
        self.assertGreater(len(self.opp.message_ids), before)

    def test_update_fields_and_tags(self):
        self.tools.execute_tool("update_opportunity_fields", {
            "name": "Test Alfa", "expected_revenue": 5000,
            "priority": "high", "tags": ["Caliente", "Demo"]})
        self.assertEqual(self.opp.expected_revenue, 5000)
        self.assertEqual(self.opp.priority, "2")
        self.assertEqual(set(self.opp.tag_ids.mapped("name")), {"Caliente", "Demo"})

    def test_find_duplicates(self):
        self.env["crm.lead"].create({
            "name": "Otra de Joan", "type": "opportunity",
            "email_from": "joan@test.example"})
        out = self.tools.execute_tool(
            "find_duplicate_opportunities", {"name": "joan@test.example"})
        self.assertIn("duplicados", out.lower())

    def test_convert_lead(self):
        lead = self.env["crm.lead"].create({
            "name": "Lead Test Gamma", "type": "lead"})
        self.tools.execute_tool(
            "convert_lead_to_opportunity", {"name": "Lead Test Gamma"})
        self.assertEqual(lead.type, "opportunity")
