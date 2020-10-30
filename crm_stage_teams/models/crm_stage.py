from odoo import api, fields, models


class Stage(models.Model):
    _inherit = 'crm.stage'

    team_ids = fields.Many2many('crm.team', string='Sales Teams', ondelete='set null',
        help='Specific team that uses this stage. Other teams will not be able to see or use this stage.')
