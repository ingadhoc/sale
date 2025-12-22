# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends("type_id")
    def _compute_project_id(self):
        res = super()._compute_project_id()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.project_id:
                order.project_id = order_type.project_id
        return res
