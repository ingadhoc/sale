from odoo import fields, models


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    pricelist_ids = fields.Many2many('product.pricelist', string='Pricelists')
