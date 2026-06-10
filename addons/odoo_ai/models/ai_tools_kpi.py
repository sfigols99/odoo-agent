import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AiToolsKpi(models.AbstractModel):
    """Pack kpi: implementaciones (specs en ai_specs/kpi.py)."""

    _inherit = "odoo.ai.tools"

    def _list_kpi_reports(self, args):
        reports = self.env["mis.report.instance"].search([], limit=20)
        if not reports:
            return "No hay informes KPI (MIS Builder) configurados."
        return "\n".join(f"- {r.name}" for r in reports)

    def _get_kpi_report(self, args):
        name = (args.get("name") or "").strip()
        inst = self.env["mis.report.instance"].search(
            [("name", "ilike", name)], limit=1)
        if not inst:
            reports = self.env["mis.report.instance"].search([], limit=10)
            return (f"No se encontró el informe «{name}». Disponibles: "
                    f"{', '.join(reports.mapped('name')) or 'ninguno'}.")
        # compute() devuelve la matriz del informe como dict (header/body).
        data = inst.compute()
        try:
            lines = [f"Informe KPI «{inst.name}»:"]
            header = (data.get("header") or [{}])[0].get("cols") or []
            if header:
                lines[0] += "  [" + " | ".join(
                    str(c.get("label") or "") for c in header) + "]"
            for row in (data.get("body") or [])[:30]:
                cells = row.get("cells") or []
                vals = " | ".join(
                    str(c.get("val_r") if c.get("val_r") is not None
                        else (c.get("val") if c.get("val") is not None else "—"))
                    for c in cells)
                lines.append(f"- {row.get('label')}: {vals or '—'}")
            return "\n".join(lines)
        except Exception:  # noqa: BLE001 - formato de matriz inesperado
            _logger.exception("Formato inesperado de MIS Builder")
            return (f"El informe «{inst.name}» se calculó pero no he podido "
                    f"interpretar su matriz; ábrelo en MIS Builder.")
