from odoo import models, api, fields


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    observations = fields.Text(
    )

    @api.constrains('sale_id')
    def set_notes(self):
        """Setamos notas internas y observaciones desde la venta
        """
        for rec in self.filtered('sale_id'):
            vals = {}
            propagate_internal_notes = self.env['ir.config_parameter'].sudo(
            ).get_param('sale.propagate_internal_notes') == 'True'
            propagate_note = self.env['ir.config_parameter'].sudo(
            ).get_param('sale.propagate_note') == 'True'
            if propagate_internal_notes and rec.sale_id.internal_notes:
                vals['note'] = rec.sale_id.internal_notes
            if propagate_note and rec.sale_id.note:
                vals['observations'] = rec.sale_id.note
            rec.write(vals)
