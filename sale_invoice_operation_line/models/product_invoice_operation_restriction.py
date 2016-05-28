# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp


class InvoiceOperationRestriction(models.Model):
    _name = 'invoice.operation.restriction'

    name = fields.Char(
        required=True,
    )
    detail_ids = fields.One2many(
        'invoice.operation.restriction.detail',
        'restriction_id',
        string='Detail',
        help='Invoice Operation Restrictions. Restriction will apply if there '
        'is a match between a journal or company of the restriction and a '
        'journal or company of an operation on the invoice or sale order',
    )
    prod_template_ids = fields.One2many(
        'product.template',
        'invoice_operation_restriction_id',
        'Products',
    )


class InvoiceOperationRestrictionDetail(models.Model):
    _name = 'invoice.operation.restriction.detail'
    # TODO esta clase podria heredar de account invoice plan line

    # template_id = fields.Many2one(
    #     'product.template',
    #     'Product',
    #     required=True,
    #     ondelete='cascade',
    #     readonly=True,
    # )
    restriction_id = fields.Many2one(
        'invoice.operation.restriction',
        required=True,
        ondelete='cascade',
        string='Restriction',
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        # default=lambda self: self.env.user.company_id,
    )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        # TODO implemet other types?
        domain="[('company_id', '=', company_id), ('type', '=', 'sale')]"
    )
    # min_percentage = fields.Float(
    #     'Min Percentage',
    #     digits=dp.get_precision('Discount'),
    #     required=True,
    #     default=0.0,
    # )
    max_percentage = fields.Float(
        'Max Percentage',
        digits=dp.get_precision('Discount'),
        required=True,
        default=100.0,
    )

    # @api.constrains('max_percentage')
    # def check_percentage(self):
    #     if self.max_percentage > 100.0:
    #         raise Warning(_(
    #             'Max percentage can not be greater than 100%%'))

    # @api.constrains('min_percentage', 'max_percentage')
    # def check_percentages(self):
    #     if self.min_percentage > self.max_percentage:
    #         raise Warning(_(
    #             'Min percentage can not be greater than max percentage'))

    @api.one
    @api.onchange('company_id')
    def onchange_company(self):
        self.journal_id = False


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    invoice_operation_restriction_id = fields.Many2one(
        'invoice.operation.restriction',
        'Invoice Operation Restrictions',
        help='Invoice Operation Restrictions. Restriction will apply if there '
        'is a match between a journal or company of the restriction and a '
        'journal or company of an operation on the invoice or sale order',
    )
