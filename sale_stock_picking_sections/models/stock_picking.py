from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_moves_by_section(self):
        """Agrupa los moves del picking por sección de la OV de origen (PLPs).

        Retorna lista de (section_name, moves_recordset).
        Mantiene el orden de secciones de la OV original.
        Si el picking no viene de una OV con secciones, retorna [(False, all_moves)].
        """
        self.ensure_one()
        moves = self.move_ids.filtered(
            lambda m: m.quantity and any(not ml.is_entire_pack for ml in m.move_line_ids)
        ).sorted(key=lambda m: (
            m.move_line_ids[0].location_id.complete_name if m.move_line_ids else "",
            m.move_line_ids[0].location_dest_id.complete_name if m.move_line_ids else "",
        ))

        sale_order = moves.mapped("sale_line_id.order_id")[:1]
        if not sale_order:
            return [(False, moves)]

        has_sections = any(
            line.display_type == "line_section" for line in sale_order.order_line
        )
        if not has_sections:
            return [(False, moves)]

        # Mapea cada sale.order.line a su sección precedente, en orden de la OV
        section_by_line_id = {}
        sections_in_ov_order = []
        current_section = False
        for line in sale_order.order_line.sorted("sequence"):
            if line.display_type == "line_section":
                current_section = line.name
                if current_section not in sections_in_ov_order:
                    sections_in_ov_order.append(current_section)
            elif not line.display_type:
                section_by_line_id[line.id] = current_section

        # Inicializa grupos vacíos en orden de OV; False al final para moves sin sección
        sections_dict = {s: self.env["stock.move"] for s in sections_in_ov_order}
        sections_dict[False] = self.env["stock.move"]

        for move in moves:
            # sale_line_id.id devuelve False si el campo está vacío
            section = section_by_line_id.get(move.sale_line_id.id, False)
            sections_dict[section] |= move

        result = [(s, sections_dict[s]) for s in sections_in_ov_order if sections_dict[s]]
        if sections_dict[False]:
            result.append((False, sections_dict[False]))
        return result
