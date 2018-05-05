##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from ast import literal_eval


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def add_products_to_quotation(self):
        self.ensure_one()
        action_read = False
        actions = self.env.ref(
            'product.product_normal_action_sell')
        if actions:
            action_read = actions.read()[0]
            context = literal_eval(action_read['context'])
            context['sale_quotation_products'] = True
            context['pricelist'] = self.pricelist_id.display_name
            # we send company in context so it filters taxes
            context['company_id'] = self.company_id.id
            context['partner_id'] = self.partner_id.id
            context['search_default_location_id'] = (
                self.warehouse_id.lot_stock_id.id)
            # context['search_default_warehouse_id'] = self.warehouse_id.id
            action_read['context'] = context
            # action_read['view_mode'] = 'tree,form'
            action_read['name'] = _('Quotation Products')
        return action_read

    @api.multi
    def add_products(self, product_ids, qty):
        self.ensure_one()
        for product in self.env['product.product'].browse(product_ids):
            sol = self.env['sale.order.line']
            last_sol = sol.search(
                [('order_id', '=', self.id)], order='sequence desc', limit=1)
            sequence = last_sol and last_sol.sequence + 1 or 10
            vals = {
                'order_id': self.id,
                'product_id': product.id or False,
                'sequence': sequence,
            }
            sol = sol.new(vals)
            # we call onchange product to get required fields
            sol.product_id_change()
            # we set qty (if we set it on create odoo overwrite it to 1)
            sol.product_uom_qty = qty
            # # we call onchange qty)
            sol.product_uom_change()
            # we convert to write
            vals = sol._convert_to_write(sol._cache)
            sol.create(vals)
