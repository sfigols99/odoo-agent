from odoo.tests.common import TransactionCase

from odoo.addons.odoo_ai.models.ai_audit import AUDITED_MODELS


class TestAuditSetup(TransactionCase):
    """Configuración de auditoría (Fase 0.4, OCA auditlog opcional)."""

    def setUp(self):
        super().setUp()
        self.audit = self.env["odoo.ai.audit"]

    def test_setup_without_auditlog_is_noop(self):
        if "auditlog.rule" in self.env:
            self.skipTest("auditlog instalado: cubierto por el test siguiente")
        # No debe lanzar ni crear nada: degradación silenciosa.
        self.assertEqual(self.audit.setup_rules(), [])

    def test_setup_with_auditlog_creates_and_is_idempotent(self):
        if "auditlog.rule" not in self.env:
            self.skipTest("auditlog no instalado en esta BD")
        created = self.audit.setup_rules()
        self.assertTrue(created)
        rules = self.env["auditlog.rule"].sudo().search(
            [("name", "like", "odoo_ai: %")])
        self.assertEqual(len(rules), len(created))
        # Segunda pasada: idempotente.
        self.assertEqual(self.audit.setup_rules(), [])

    def test_audited_models_cover_write_tools(self):
        # Los modelos que tocan las tools de escritura actuales deben estar
        # en AUDITED_MODELS (recordatorio al añadir packs nuevos).
        for model in ("crm.lead", "sale.order", "purchase.order",
                      "account.move"):
            self.assertIn(model, AUDITED_MODELS)
