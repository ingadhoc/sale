from odoo import models


class IrRule(models.Model):
    _inherit = "ir.rule"

    def _get_rules(self, model_name, mode="read"):
        rules = super()._get_rules(model_name, mode=mode)
        if self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            portal_rule = self.env.ref("sale.sale_order_rule_portal", raise_if_not_found=False)
            if portal_rule:
                rules -= portal_rule
        return rules
