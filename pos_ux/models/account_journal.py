##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    pos_outstanding_payment = fields.Boolean()
