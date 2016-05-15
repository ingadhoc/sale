# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp


class ProductInvoiceOperationRestriction(models.Model):
    _name = 'product.invoice.operation.restriction'

    # template_id = fields.Many2one(
    #     'product.template',
    #     'Product',
    #     required=True,
    #     ondelete='cascade',
    #     readonly=True,
    # )
    name = fields.Char(
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        # TODO implemet other types?
        domain="[('company_id', '=', company_id), ('type', '=', 'sale')]"
    )
    min_percentage = fields.Float(
        'Min Percentage',
        digits=dp.get_precision('Discount'),
        required=True,
        default=0.0,
    )
    max_percentage = fields.Float(
        'Max Percentage',
        digits=dp.get_precision('Discount'),
        required=True,
        default=100.0,
    )
    prod_template_ids = fields.Many2many(
        'product.template',
        'product_invoice_operation_resteriction_rel',
        'restriction_id', 'template_id',
        'Products',
    )

    @api.constrains('min_percentage', 'max_percentage')
    def check_percentages(self):
        if self.min_percentage > self.max_percentage:
            raise Warning(_(
                'Minn percentage can not be greater than max percentage'))


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    invoice_operation_restriction_ids = fields.Many2many(
        'product.invoice.operation.restriction',
        'product_invoice_operation_resteriction_rel',
        'template_id', 'restriction_id',
        'Invoice Op. Restrictions',
        help='Invoice Operation Restrictions',
    )
