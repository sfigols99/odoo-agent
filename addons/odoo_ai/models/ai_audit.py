import logging

from odoo import models
from odoo.tools import config

_logger = logging.getLogger(__name__)

# Modelos que las tools de ESCRITURA del asistente pueden modificar. Si el
# módulo OCA `auditlog` está instalado, se crean reglas de auditoría para
# ellos: traza independiente (quién/qué/cuándo) complementaria al historial
# de la conversación. Amplíalo al añadir packs con escrituras nuevas.
AUDITED_MODELS = [
    "crm.lead",
    "sale.order",
    "purchase.order",
    "account.move",
    "account.payment",
]


class AiAudit(models.AbstractModel):
    _name = "odoo.ai.audit"
    _description = "Configuración de auditoría del Asistente IA (OCA auditlog)"

    def setup_rules(self):
        """Crea (idempotente) las reglas de auditlog para AUDITED_MODELS.

        Se invoca desde el post_init_hook del addon y desde la acción de
        servidor «Configurar auditoría del Asistente IA» (por si auditlog se
        instala DESPUÉS que odoo_ai). Sin auditlog instalado, no hace nada.
        """
        if "auditlog.rule" not in self.env:
            _logger.info("odoo_ai: auditlog no instalado; sin reglas de auditoría")
            return []
        Rule = self.env["auditlog.rule"].sudo()
        IrModel = self.env["ir.model"].sudo()
        created = []
        for model_name in AUDITED_MODELS:
            model = IrModel.search([("model", "=", model_name)], limit=1)
            if not model:
                continue  # módulo del modelo no instalado en esta BD
            rule_name = f"odoo_ai: {model_name}"
            if Rule.search([("name", "=", rule_name)], limit=1):
                continue  # ya configurada (idempotencia)
            rule = Rule.create({
                "name": rule_name,
                "model_id": model.id,
                "log_create": True,
                "log_write": True,
                "log_unlink": True,
                # 'fast' no captura valores antes/después completos pero apenas
                # penaliza; cambia a 'full' si necesitas el diff de campos.
                "log_type": "fast",
            })
            # subscribe() parchea create/write/unlink en el modelo auditado
            # (auditlog_ruled_*). Bajo --test-enable, el detector de fugas de
            # Odoo 18 considera esos atributos añadidos en runtime como una
            # fuga y hace fallar tests ajenos. En modo test creamos la regla
            # pero NO la suscribimos (la auditoría real se activa en producción
            # vía post_init_hook / la acción de servidor).
            if not config["test_enable"]:
                try:
                    rule.subscribe()
                except Exception:  # noqa: BLE001 - la regla queda en borrador
                    _logger.exception(
                        "odoo_ai: no se pudo suscribir la regla %s", rule_name)
            created.append(model_name)
        if created:
            _logger.info("odoo_ai: reglas de auditoría creadas para %s", created)
        return created
