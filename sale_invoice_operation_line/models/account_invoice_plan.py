# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
# from openerp import models, api


# class AccountInvoicePlan(models.Model):
#     _inherit = 'account.invoice.plan'

#     @api.multi
#     def recreate_operations(self, res_id, model):
#         res = super(AccountInvoicePlan, self).recreate_operations(
#             res_id, model)
#         self.env[model].browse(res_id).update_operations_lines()
#         return res
