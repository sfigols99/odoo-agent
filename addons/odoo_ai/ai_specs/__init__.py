# Registro declarativo de tools, partido en PACKS por dominio (Fase 0.1 del
# roadmap). Este paquete es PURO (sin imports de Odoo): el harness de evals
# (Fase 0.6) lo importa standalone para obtener los schemas.
#
# Cada pack define: PACK (nombre), PACK_DESCRIPTION (para el router de la
# Fase 0.2), SPECS (lista de tools) y DESCRIPTIONS (tarjeta de confirmación).
# Aquí se agregan añadiendo la clave "pack" a cada spec.
from . import account, crm, purchase, sale, stock

PACKS = [stock, crm, sale, account, purchase]

TOOL_SPECS = [dict(spec, pack=mod.PACK) for mod in PACKS for spec in mod.SPECS]

DESCRIPTIONS = {
    name: fmt for mod in PACKS for name, fmt in mod.DESCRIPTIONS.items()
}

PACK_NAMES = [mod.PACK for mod in PACKS]
PACK_INFO = {mod.PACK: mod.PACK_DESCRIPTION for mod in PACKS}

# Integridad en tiempo de import: nombres de tool únicos en todo el catálogo.
_names = [s["schema"]["function"]["name"] for s in TOOL_SPECS]
assert len(_names) == len(set(_names)), (
    "Nombres de tool duplicados entre packs: "
    + str(sorted({n for n in _names if _names.count(n) > 1})))
del _names
