import logging

from odoo import models
from odoo.exceptions import AccessError, UserError, ValidationError

# Los specs viven en ai_specs/ (paquete puro, partido por packs de dominio).
# Se re-exportan aquí por compatibilidad con imports existentes.
from ..ai_specs import DESCRIPTIONS, PACK_INFO, PACK_NAMES, TOOL_SPECS  # noqa: F401

_logger = logging.getLogger(__name__)


class AiTools(models.AbstractModel):
    """Registro y despacho de herramientas del Asistente IA.

    Las implementaciones de las tools viven en mixins por dominio
    (ai_tools_stock.py, ai_tools_crm.py, ...) que heredan de este modelo.
    """

    _name = "odoo.ai.tools"
    _description = "Registro de herramientas del Asistente IA (ORM en proceso)"

    # ---------------- Registro condicional / despacho ----------------
    def _installed_modules(self):
        """Conjunto de módulos instalados (cacheado por petición)."""
        mods = self.env["ir.module.module"].sudo().search(
            [("state", "=", "installed")])
        return set(mods.mapped("name"))

    def _is_available(self, spec, installed=None):
        """Una tool está disponible si todos sus módulos `requires` lo están.

        Las tools sin `requires` (core: stock, account, purchase...) siempre
        están disponibles. Este es el punto de extensión para integrar módulos
        OCA: cada tool nueva declara `requires=["nombre_modulo_oca"]` y solo
        aparece cuando ese módulo está instalado.
        """
        requires = spec.get("requires")
        if not requires:
            return True
        if installed is None:
            installed = self._installed_modules()
        return all(m in installed for m in requires)

    def _available_specs(self):
        installed = self._installed_modules()
        return [s for s in TOOL_SPECS if self._is_available(s, installed)]

    def get_tool_schemas(self, packs=None):
        """Schemas de las tools disponibles, opcionalmente filtrados por packs.

        Solo se exponen al LLM las tools cuyos módulos están instalados; si se
        pasa `packs` (lista de nombres), se limita además a esos dominios
        (selección dinámica, Fase 0.2).
        """
        specs = self._available_specs()
        if packs is not None:
            specs = [s for s in specs if s["pack"] in packs]
        return [s["schema"] for s in specs]

    def list_packs(self):
        """Packs con al menos una tool disponible: {nombre: descripción}."""
        available = {s["pack"] for s in self._available_specs()}
        return {p: PACK_INFO[p] for p in PACK_NAMES if p in available}

    def _spec(self, name):
        return next(
            (s for s in TOOL_SPECS if s["schema"]["function"]["name"] == name),
            None,
        )

    def is_write_tool(self, name):
        spec = self._spec(name)
        return bool(spec and spec["is_write"])

    def describe_action(self, name, args):
        fmt = DESCRIPTIONS.get(name)
        return fmt(args or {}) if fmt else f"Ejecutar «{name}» con {args}."

    def execute_tool(self, name, args):
        spec = self._spec(name)
        if not spec:
            return f"Error: herramienta desconocida «{name}»."
        if not self._is_available(spec):
            return (f"La herramienta «{name}» no está disponible: requiere los "
                    f"módulos {spec.get('requires')} (no instalados).")
        method = getattr(self, spec["method"], None)
        if method is None:
            return f"Error: implementación no encontrada para «{name}»."
        try:
            return method(args or {})
        except (AccessError, UserError, ValidationError) as e:
            return f"No se pudo completar: {e}"
        except Exception as e:  # noqa: BLE001 - se devuelve al modelo como texto
            _logger.exception("Tool %s falló", name)
            return f"Error ejecutando «{name}»: {e}"
