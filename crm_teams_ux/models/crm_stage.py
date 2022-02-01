from odoo import fields, models


class Stage(models.Model):
    _inherit = 'crm.stage'

    team_ids = fields.Many2many('crm.team', string="Sales Teams", ondelete='cascade')
