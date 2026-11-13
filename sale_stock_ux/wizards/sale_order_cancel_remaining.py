from odoo import api, fields, models


class TaskStopRunningTimersConfirmation(models.TransientModel):
    _name = "sale.order.cancel.remaining"
    _description = "Sale Order Cancel Remaining"

    sale_order_line_ids = fields.Many2many(
        "sale.order.line", required=True, default=lambda self: self.default_sale_order_line_ids()
    )
    lost_reason_id = fields.Many2one("sale.order.line.lost.reason", string="Unsold Reason")
    lost_qty_enabled = fields.Boolean(compute="_compute_lost_qty_enabled")

    @api.model
    def default_sale_order_line_ids(self):
        return self.env["sale.order"].browse(self.env.context.get("active_ids", [])).mapped("order_line")

    def _compute_lost_qty_enabled(self):
        self.lost_qty_enabled = self.env.user.has_group("sale_ux.group_lost_qty")

    def action_confirm(self):
        self.sale_order_line_ids.filtered(lambda x: x.delivery_status == "to deliver").with_context(
            cancel_from_order=True, cancel_lost_reason_id=self.lost_reason_id.id
        ).button_cancel_remaining()
