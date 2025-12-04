##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    only_packagings = fields.Boolean(
        default=False,
        help="Indicates that this product is only used as packaging and does not use units.",
    )

    def _get_available_uoms(self):
        self.ensure_one()
        res = super()._get_available_uoms()
        if self.only_packagings:
            return self.uom_ids
        return res
