##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


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
                    res[r] = {"error": "SaleOrder not matching"}
        return res
