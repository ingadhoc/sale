##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models,  _
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def add_products_to_quotation(self):
        self.ensure_one()
        action_read = self.env["ir.actions.act_window"]._for_xml_id('product.product_normal_action_sell')
        context = safe_eval(action_read['context'])
        context.update(dict(
            # we send by context to show the price of product pack detailed for component if exist
            sale_quotation_products=True,
            whole_pack_price=True,
            pricelist=self.pricelist_id.id,
            # we send company in context so it filters taxes
            company_id=self.company_id.id,
            partner_id=self.partner_id.id,
        ))
        # we do this apart because we need to ensure "warehouse_id" exists in datebase, if for the case that
        # we don't have inventory installed yet
        # for this to work stock_ux needs to be installed because it's adding those filters on every view
        if 'warehouse_id' in self._fields:
            context.update(dict(
                search_default_location_id=self.warehouse_id.lot_stock_id.id,
            ))
        action_read.update(
            context=context,
            name=_('Quotation Products'),
        )
        return action_read

    def add_products(self, product_ids, qty):
        self.ensure_one()
        sol = self.env['sale.order.line']
        for product in self.env['product.product'].browse(product_ids):
            last_sol = sol.search(
                [('order_id', '=', self.id)], order='sequence desc', limit=1)
            sequence = last_sol and last_sol.sequence + 1 or 10
            vals = {
                'order_id': self.id,
                'product_uom_qty': qty, 
                'product_id': product.id or False,
                'sequence': sequence,
                'company_id': self.company_id.id,
            }
            sol.create(vals)

    def action_add_from_catalog(self):
        # Replaces the product's kanban view by the purchase specific one.
        action = super().action_add_from_catalog()
        tree_view_id = self.env.ref('product.product_product_tree_view').id
        kanban_view_id = self.env.ref('product.product_view_kanban_catalog').id
        action['views'] = [(tree_view_id, 'tree'), (kanban_view_id, 'kanban')]
        return action
