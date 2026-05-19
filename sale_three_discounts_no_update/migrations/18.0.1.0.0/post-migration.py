from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.cr.execute(
        """
        UPDATE product_pricelist_item
           SET compute_price = 'formula',
               price_discount = percent_price
         WHERE compute_price = 'percentage'
        """
    )
