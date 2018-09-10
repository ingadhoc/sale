##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def add_products_to_quotation(self):
        self.ensure_one()
        action_read = False
        actions = self.env.ref('product.product_normal_action_sell')
        if actions:
            action_read = actions.read()[0]
            context = safe_eval(action_read['context'])
            context.update(dict(
                sale_quotation_products=True,
                pricelist=self.pricelist_id.display_name,
                # we send company in context so it filters taxes
                company_id=self.company_id.id,
                partner_id=self.partner_id.id,
                search_default_location_id=self.warehouse_id.lot_stock_id.id,
                # search_default_warehouse_id=self.warehouse_id.id,
            ))
            action_read.update(
                context=context,
                # view_mode='tree,form'.
                name=_('Quotation Products'),
            )
            action_read['context'] = context
        return action_read

    @api.multi
    def add_products(self, product_ids, qty):
        self.ensure_one()
        sol = self.env['sale.order.line']
        for product in self.env['product.product'].browse(product_ids):
            last_sol = sol.search(
                [('order_id', '=', self.id)], order='sequence desc', limit=1)
            sequence = last_sol and last_sol.sequence + 1 or 10
            vals = {
                'order_id': self.id,
                'product_id': product.id or False,
                'sequence': sequence,
                'company_id': self.company_id.id,
            }
            sol = sol.new(vals)
            sol.product_id_change()
            sol.product_uom_qty = qty
            sol.product_uom_change()
            vals = sol._convert_to_write(sol._cache)
            sol.create(vals)
