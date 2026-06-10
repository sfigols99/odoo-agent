from odoo import models


class AiToolsProject(models.AbstractModel):
    """Pack project: implementaciones (specs en ai_specs/project.py)."""

    _inherit = "odoo.ai.tools"

    def _create_task(self, args):
        project = self.env["project.project"].search(
            [("name", "ilike", args.get("project_name") or "")], limit=1)
        if not project:
            projects = self.env["project.project"].search([], limit=10)
            return (f"No se encontró el proyecto «{args.get('project_name')}». "
                    f"Disponibles: {', '.join(projects.mapped('name')) or 'ninguno'}.")
        vals = {
            "name": (args.get("title") or "").strip() or "Tarea",
            "project_id": project.id,
        }
        if args.get("description"):
            vals["description"] = args["description"]
        if args.get("assignee"):
            # active_test=False: algunos usuarios reales (p. ej. el bot del
            # sistema) están inactivos pero son asignables.
            user = self.env["res.users"].with_context(active_test=False).search(
                [("name", "ilike", args["assignee"])], limit=1)
            if not user:
                return f"No se encontró el usuario «{args['assignee']}»."
            vals["user_ids"] = [(6, 0, user.ids)]
        task = self.env["project.task"].create(vals)
        return (f"Tarea creada en «{project.name}»: [{task.id}] {task.name}"
                f" (etapa: {task.stage_id.name or '—'}).")

    def _list_my_tasks(self, args):
        tasks = self.env["project.task"].search(
            [("user_ids", "in", self.env.user.id)],
            limit=20, order="date_deadline asc, id desc")
        tasks = tasks.filtered(lambda t: not t.stage_id.fold)
        if not tasks:
            return "No tienes tareas abiertas."
        return "\n".join(
            f"[{t.id}] {t.name} — proyecto: {t.project_id.name or '—'} — "
            f"etapa: {t.stage_id.name or '—'}"
            f"{(' — vence ' + str(t.date_deadline)) if t.date_deadline else ''}"
            for t in tasks)
