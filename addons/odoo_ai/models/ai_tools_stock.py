from odoo import models


class AiToolsStock(models.AbstractModel):
    """Pack stock: implementaciones (specs en ai_specs/stock.py)."""

    _inherit = "odoo.ai.tools"

    def _check_stock(self, args):
        name = (args.get("product_name") or "").strip()
        if not name:
            return "Falta el nombre del producto."
        prods = self.env["product.product"].search(
            [("name", "ilike", name)], limit=5)
        if not prods:
            return f"No se encontró ningún producto que coincida con «{name}»."
        # Con OCA stock_available_unreserved, añade el stock sin reservar.
        has_unres = "qty_available_not_res" in self.env["product.product"]._fields
        lines = []
        for p in prods:
            line = (f"{p.display_name}: {p.qty_available} a mano, "
                    f"{p.free_qty} libres, {p.virtual_available} previstas")
            if has_unres:
                line += f", {p.qty_available_not_res} sin reservar"
            lines.append(line + f" (UoM: {p.uom_id.name}).")
        return "\n".join(lines)

    def _list_low_stock(self, args):
        threshold = float(args.get("threshold") or 5)
        # En Odoo 17/18 los tipos product/consu se fusionaron y la
        # "almacenabilidad" pasó al booleano is_storable; solo esos productos
        # tienen stock real que controlar. Filtramos en el dominio para no
        # perder coincidencias más allá del límite de búsqueda.
        prods = self.env["product.product"].search(
            [("is_storable", "=", True), ("qty_available", "<=", threshold)],
            limit=30, order="qty_available asc")
        if not prods:
            return f"No hay productos con stock por debajo de {threshold}."
        return "\n".join(
            f"{p.display_name}: {p.qty_available}" for p in prods)

    # ================== Albaranes / transferencias (Ola 4) ==================
    def _list_pending_pickings(self, args):
        picks = self.env["stock.picking"].search(
            [("state", "in", ["waiting", "confirmed", "assigned"])],
            limit=20, order="scheduled_date asc")
        if not picks:
            return "No hay albaranes pendientes."
        state_lbl = {"waiting": "en espera", "confirmed": "confirmado",
                     "assigned": "preparado"}
        return "\n".join(
            f"{p.name} — {p.picking_type_id.name} — "
            f"{p.partner_id.display_name or '—'} — "
            f"{state_lbl.get(p.state, p.state)} — prevista {p.scheduled_date or '—'}"
            for p in picks)

    def _validate_picking(self, args):
        name = (args.get("picking_name") or "").strip()
        if not name:
            return "Falta el número del albarán."
        pick = self.env["stock.picking"].search([("name", "=", name)], limit=1)
        if not pick:
            return f"No se encontró el albarán «{name}»."
        if pick.state == "done":
            return f"El albarán {pick.name} ya está validado."
        if pick.state not in ("assigned", "confirmed"):
            return (f"El albarán {pick.name} no está listo para validar "
                    f"(estado: {pick.state}).")
        res = pick.button_validate()
        # button_validate puede devolver un wizard (p. ej. confirmación de
        # backorder) que requiere decisión humana en la UI.
        if isinstance(res, dict) and res.get("res_model"):
            return (f"El albarán {pick.name} requiere una decisión adicional "
                    f"({res.get('res_model')}, p. ej. crear backorder): "
                    f"complétalo desde la vista de Inventario.")
        return f"Albarán {pick.name} validado. Estado: {pick.state}."

    # ============ Extensiones OCA (Ola 4; registro condicional) ============
    def _start_inventory_adjustment(self, args):
        # OCA stock_inventory: modelo stock.inventory (draft/in_progress/done).
        product = self.env["product.product"].search(
            [("name", "ilike", args.get("product_name") or "")], limit=1)
        if not product:
            return f"No se encontró el producto «{args.get('product_name')}»."
        inv = self.env["stock.inventory"].create({
            "name": (args.get("name")
                     or f"Ajuste IA: {product.display_name}"),
            "product_ids": [(6, 0, product.ids)],
        })
        inv.action_state_to_in_progress()
        return (f"Ajuste de inventario «{inv.name}» iniciado (estado: "
                f"{inv.state}) para {product.display_name}. Registra los "
                f"conteos desde Inventario → Ajustes.")

    def _list_inventory_adjustments(self, args):
        invs = self.env["stock.inventory"].search(
            [("state", "in", ["draft", "in_progress"])],
            limit=20, order="id desc")
        if not invs:
            return "No hay ajustes de inventario abiertos."
        return "\n".join(
            f"[{i.id}] {i.name} — estado: {i.state}"
            for i in invs)
