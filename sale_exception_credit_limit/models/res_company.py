##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _post_init_credit(self):
        self.search([]).write({'account_use_credit_limit':True})
