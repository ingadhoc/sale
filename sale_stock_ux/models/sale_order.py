##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    force_delivery_status = fields.Selection(
        [
            ("full", "Fully Delivered"),
        ],
        tracking=True,
        copy=False,
    )

    with_returns = fields.Boolean(
        compute="_compute_with_returns",
        store=True,
    )

    @api.depends("order_line.quantity_returned")
    def _compute_with_returns(self):
        for order in self:
            order.with_returns = any(line.quantity_returned for line in order.order_line)

    def action_cancel(self):
        self = self.with_context(cancel_from_order=True)
        for order in self.filtered(lambda order: order.picking_ids.filtered(lambda x: x.state == "done")):
            raise UserError(
                _("Unable to cancel sale order %s as some deliveries have already been done.") % (order.name)
            )
        return super().action_cancel()

    @api.depends(
        "picking_ids",
        "picking_ids.state",
        "force_delivery_status",
        "order_line.qty_delivered",
        "order_line.product_uom_qty",
    )
    def _compute_delivery_status(self):
        """
        Compute delivery status considering both storable products and services.
        """
        super()._compute_delivery_status()
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        for order in self:
            if order.force_delivery_status:
                order.delivery_status = order.force_delivery_status
                continue

            consu_lines = order.order_line.filtered(lambda l: l.product_id.type == "consu")
            service_lines = order.order_line.filtered(lambda l: l.product_id.type == "service")

            if not consu_lines and not service_lines:
                order.delivery_status = False
                continue

            if not service_lines:
                continue

            service_fully_delivered = service_partially_delivered = True
            for line in service_lines:
                delivered, ordered = line.qty_delivered, line.product_uom_qty
                if float_compare(delivered, ordered, precision_digits=precision) < 0:
                    service_fully_delivered = False
                    if float_compare(delivered, 0.0, precision_digits=precision) == 0:
                        service_partially_delivered = False
                        break

            service_status = (
                "full" if service_fully_delivered else ("partial" if service_partially_delivered else "pending")
            )

            if not consu_lines:
                order.delivery_status = service_status
                continue

            consu_status = order.delivery_status
            if consu_status == "full" and service_status == "full":
                order.delivery_status = "full"
            elif consu_status in ("partial", "full") or service_status in ("partial", "full"):
                order.delivery_status = "partial"
            else:
                order.delivery_status = "pending"

    def write(self, vals):
        self.check_force_delivery_status(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.check_force_delivery_status(vals)
        return super().create(vals_list)

    @api.model
    def check_force_delivery_status(self, vals):
        if vals.get("force_delivery_status") and not self.env.user.has_group("base.group_system"):
            group = self.env.ref("base.group_system").sudo()
            raise UserError(
                _('Only users with "%s / %s" can Set Delivered manually') % (group.category_id.name, group.name)
            )
