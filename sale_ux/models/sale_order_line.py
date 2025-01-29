##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    date_order = fields.Datetime("Order Date", related="order_id.date_order")

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

    def action_sale_history(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_ux.action_sale_order_line_usability_tree")
        action['domain'] = [('state', 'in', ['sale', 'done']), ('product_id', '=', self.product_id.id)]
        action['display_name'] = _("Sale History for %s", self.product_id.display_name)
        action['context'] = {
            'search_default_order_partner_id': self.order_partner_id.parent_id.id or self.order_partner_id.id,
            'search_default_partner_id': 1
        }
        return action

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if lines.filtered(lambda x: x.order_id and x.order_id.state == 'done'):
            raise ValidationError(_("You cannot add lines to blocked sale orders."))
        return lines

    def _get_protected_fields(self):
        return super()._get_protected_fields() + ['discount']
