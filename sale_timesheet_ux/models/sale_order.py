from odoo import models, api


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.depends('order_line.product_id.project_id')
    def _compute_tasks_ids(self):
        for order in self:
            order.tasks_ids = self.env['project.task'].search(['&', ('display_project_id', '!=', 'False'), '|','|', ('sale_line_id', 'in', order.order_line.ids), ('sale_order_id', '=', order.id), ('order_id', '=', order.id)])
            order.tasks_count = len(order.tasks_ids)
