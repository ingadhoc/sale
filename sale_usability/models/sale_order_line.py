# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # add context so show sale data by default
    order_id = fields.Many2one(
        context={'show_sale': True}
    )

    @api.depends('order_id.manually_set_invoiced')
    def _compute_invoice_status(self):
        """
        Sobreescribimos directamente el invoice status y no el qty_to_invoice
        ya que no nos importa tipo de producto y lo hace mas facil.
        Ademas no molesta dependencias con otros modulos que ya sobreescribian
        _get_to_invoice_qty
        """
        super(SaleOrderLine, self)._compute_invoice_status()
        for line in self:
            # solo seteamos facturado si en sale o done
            if line.order_id.state not in ['sale', 'done']:
                continue
            if line.order_id.manually_set_invoiced:
                line.invoice_status = 'invoiced'
