from openerp import models, api


class stock_move(models.Model):
    _inherit = "stock.move"

    @api.model
    def _get_invoice_line_vals(self, move, partner, inv_type):
        res = super(stock_move, self)._get_invoice_line_vals(
            move, partner, inv_type)
        if inv_type in ('out_invoice', 'out_refund') and move.procurement_id and move.procurement_id.sale_line_id:
            sale_line = move.procurement_id.sale_line_id
            res['discount1'] = sale_line.discount1
            res['discount2'] = sale_line.discount2
            res['discount3'] = sale_line.discount3
        return res
