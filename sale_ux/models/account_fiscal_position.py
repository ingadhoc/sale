from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    deduct_price_included_taxes = fields.Boolean(
        string='Deduct Price-Included Taxes',
        help="In sales: When this fiscal position is set, if the product has taxes included in the price, "
             "they will be deducted from the price calculation when mapping to new taxes."
    )

