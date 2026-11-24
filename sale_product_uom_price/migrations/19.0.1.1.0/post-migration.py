##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Quotations entered before the price per product unit was rounded."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["sale.order.line"]._round_open_quotations_price_unit_product_uom()
