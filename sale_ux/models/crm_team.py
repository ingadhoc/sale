##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    member_ids = fields.Many2many(domain="[]")
