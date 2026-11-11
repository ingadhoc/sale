##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _distributor_sudo(self):
        """The portal distributor must not read the bills of materials, but the stock fields of an order
        line look at them to know if the product is a kit (sale_mrp). Those fields are computed as
        superuser for the distributor, as the margin ones are in portal_sale_distributor."""
        if self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            return self.sudo()
        return self

    def _compute_qty_to_deliver(self):
        super(SaleOrderLine, self._distributor_sudo())._compute_qty_to_deliver()

    def _compute_qty_at_date(self):
        super(SaleOrderLine, self._distributor_sudo())._compute_qty_at_date()

    def _compute_is_mto(self):
        super(SaleOrderLine, self._distributor_sudo())._compute_is_mto()
