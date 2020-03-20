from odoo import models, fields


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    number = fields.Integer(
        compute='_compute_get_number',
    )

    def _compute_get_number(self):
        """No es lo mas elegante pero funciona. Algunos comentarios:
        * para evitar computos de mas no dejamos el depends y no se computa con los onchange
        * para hacer eso nos fijamos si lo que viene en self son new ids o enteros.
        * asignamos self.number porque si no da error, aparentemente por algo del mapped y el order.order_line.number
        """
        self.number = False
        if self and not isinstance(self[0].id, int):
            return
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line.sorted("sequence"):
                line.number = number
                number += 1
