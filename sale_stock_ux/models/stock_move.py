##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    sale_id = fields.Many2one(
        related='group_id.sale_id',
    )

    def _get_new_picking_values(self):
        """ return create values for new picking that will be linked with group
        of moves in self.
        """
        res = super()._get_new_picking_values()
        values = {}
        sale = self.mapped('group_id.sale_id')
        propagate_internal_notes = self.env['ir.config_parameter'].sudo(
        ).get_param('sale.propagate_internal_notes') == 'True'
        propagate_note = self.env['ir.config_parameter'].sudo(
        ).get_param('sale.propagate_note') == 'True'
        if propagate_internal_notes and sale.internal_notes:
            values['note'] = sale.internal_notes
        if propagate_note and sale.note:
            values['observations'] = sale.note
        if values:
            res.update(values)

        return res
