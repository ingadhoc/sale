##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('order_id.force_invoiced_status')
    def _compute_invoice_status(self):
        """
        Sobreescribimos directamente el invoice status y no el qty_to_invoice
        ya que no nos importa tipo de producto y lo hace mas facil.
        Ademas no molesta dependencias con otros modulos que ya sobreescribian
        _get_to_invoice_qty
        """
        super()._compute_invoice_status()
        for line in self:
            # solo seteamos facturado si en sale o done
            if line.order_id.state not in ['sale', 'done']:
                continue
            if line.order_id.force_invoiced_status:
                line.invoice_status = line.order_id.force_invoiced_status

    def _compute_amount(self):
        """ Idem modificacion en sale.order._amount_by_group
        """
        for line in self:
            date_order = line.order_id.date_order or fields.Date.context_today(line)
            line.env.context.date_invoice = date_order
            line.env.context.invoice_company = line.company_id
            super(SaleOrderLine, line)._compute_amount()
