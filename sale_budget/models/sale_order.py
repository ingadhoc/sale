from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_create_budget(self):
        view = self.env.ref("sale_budget.crossovered_budget_view_tree")
        return {
            "name": _("Details"),
            "view_mode": "tree",
            "res_model": "crossovered.budget",
            "view_id": view.id,
            "type": "ir.actions.act_window",
            "target": "new",
            "readonly": True,
            # "res_id": self.id,
            # "context": dict(self.env.context, pricelist=self.order_id.pricelist_id.id),
        }
