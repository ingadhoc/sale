##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
<<<<<<< 9e6d22dd7937e69f09a78ee9551e4fc221691f75
from odoo import api, fields, models
||||||| 2eda38dc6b5fe2268a9aacb7765a03c97047a64a
from odoo import models
=======
from odoo import _, models
>>>>>>> 927ebdf3ff6c75258846f4c41a95dcb69265bc83


class SaleOrder(models.Model):
    _inherit = "sale.order"

    loyalty_rewards_banner_visible = fields.Boolean(
        compute="_compute_loyalty_rewards_banner_visible",
    )

    @api.depends(
        "state",
        "partner_id",
        "pricelist_id",
        "company_id",
        "order_line.reward_id",
        "order_line.is_reward_line",
        "order_line.product_id",
        "order_line.product_uom_qty",
        "order_line.discount",
        "order_line.price_unit",
        "order_line.coupon_id",
        "applied_coupon_ids",
        "coupon_point_ids",
    )
    def _compute_loyalty_rewards_banner_visible(self):
        # The banner is a salesperson tool, and looking for claimable rewards ends up reading the
        # company contact (_get_program_timezone), which portal users can not read. Computing it
        # for them raises an AccessError that keeps the sale order form from opening.
        is_internal_user = self.env.user.has_group("base.group_user")
        for order in self:
            order.loyalty_rewards_banner_visible = False
            if not is_internal_user:
                continue
            if order.state not in ("draft", "sent"):
                continue
            if order.order_line.filtered("is_reward_line"):
                continue
            if order._get_claimable_rewards() or any(order._get_applicable_program_points().values()):
                order.loyalty_rewards_banner_visible = True

    def _program_check_compute_points(self, programs):
        res = super()._program_check_compute_points(programs)
        for r in res:
            domain = r._get_valid_sale_order()
            if not res[r].get("error") and domain:
                if self not in self.env["sale.order"].search(domain):
<<<<<<< 9e6d22dd7937e69f09a78ee9551e4fc221691f75
                    res[r] = {
                        "error": r.not_applicable_message
                        or self.env._(
                            "This promotion cannot be applied because this sales order does not meet"
                            ' the conditions required by the program "%(program)s".',
                            program=r.name,
                        )
                    }
||||||| 2eda38dc6b5fe2268a9aacb7765a03c97047a64a
                    res[r] = {"error": "SaleOrder not matching"}
=======
                    res[r] = {
                        "error": r.not_applicable_message
                        or _(
                            "This promotion cannot be applied because this sales order does not meet"
                            ' the conditions required by the program "%(program)s".',
                            program=r.name,
                        )
                    }
>>>>>>> 927ebdf3ff6c75258846f4c41a95dcb69265bc83
        return res
