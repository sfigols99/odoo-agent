from . import models


def post_init_hook(env):
    """Al instalar el addon: configura las reglas de auditlog si está presente."""
    env["odoo.ai.audit"].setup_rules()
