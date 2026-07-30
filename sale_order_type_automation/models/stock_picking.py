##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        """
        On picking confirmation we check if invoice should be created
        """
        automation_context = self._get_background_post_automation_context()
        self = self.with_context(**automation_context)
        res = super()._action_done()
        sale_orders = (
            self.filtered(lambda p: p.location_id.usage == "customer" or p.location_dest_id.usage == "customer")
            .sudo()
            .mapped("sale_id")
        )
        sale_orders.run_invoicing_atomation()
        if automation_context.get("background_post_batch_defer"):
            self._notify_background_post_batch_defer()
        return res

    def _get_invoicing_automation_orders(self):
        return (
            self.sudo()
            .mapped("sale_id")
            .filtered(lambda x: x.type_id.invoicing_atomation == "validate_invoice" and not x.type_id.background_post)
        )

    def _get_background_post_automation_context(self):
        move = self.env["account.move"]
        if self.env.context.get("background_post_confirming_order") or not move._background_post_available():
            return {}
        ctx = {"background_post_picking_ids": self.ids}
        if len(self) > move._get_background_post_batch_size() and self._get_invoicing_automation_orders():
            ctx["background_post_defer"] = True
            ctx["background_post_batch_defer"] = True
        return ctx

    def _notify_background_post_batch_defer(self):
        self.env.user._bus_send(
            "simple_notification",
            {
                "type": "info",
                "title": self.env._("Invoices to be validated in the background"),
                "message": self.env._(
                    "You validated %(count)s transfers at once, so their invoices were created and "
                    "left to be validated by the background post process.",
                    count=len(self),
                ),
                "sticky": True,
            },
        )

    def action_validate_force_background_post(self):
        res = self.with_context(background_post_defer=True).button_validate()
        return res if isinstance(res, dict) else self._get_records_action()
