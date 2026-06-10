from .common import _fn

PACK = "project"
PACK_DESCRIPTION = ("Proyectos: crear tareas y consultar mis tareas "
                    "pendientes.")

# Requieren el módulo CORE `project` (el addon no depende de él: registro
# condicional también sirve para módulos core opcionales).
SPECS = [
    {"is_write": True, "requires": ["project"], "method": "_create_task",
     "schema": _fn(
        "create_task",
        "Crea una tarea en un proyecto.",
        {"project_name": {"type": "string", "description": "Nombre del proyecto."},
         "title": {"type": "string", "description": "Título de la tarea."},
         "description": {"type": "string", "description": "Descripción (opcional)."},
         "assignee": {"type": "string",
                      "description": "Usuario asignado (opcional)."}},
        ["project_name", "title"])},
    {"is_write": False, "requires": ["project"], "method": "_list_my_tasks",
     "schema": _fn(
        "list_my_tasks",
        "Lista mis tareas de proyecto abiertas.",
        {})},
]

DESCRIPTIONS = {
    "create_task": lambda a: (
        f"Crear la tarea «{a.get('title')}» en el proyecto "
        f"«{a.get('project_name')}»"
        f"{(' asignada a ' + a['assignee']) if a.get('assignee') else ''}."),
}
