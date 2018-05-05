# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class res_company(models.Model):
    _inherit = "res.company"

    sale_order_validity_days = fields.Integer(
        'Sale Order Validity Days',
        help='Set days of validity for Sales Order, if null, no validity date '
        'will be filled')
