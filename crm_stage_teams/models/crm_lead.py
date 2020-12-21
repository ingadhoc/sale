from odoo import fields, models, SUPERUSER_ID


class Lead(models.Model):
    _inherit = 'crm.lead'

    stage_id = fields.Many2one(
        'crm.stage', string='Stage', ondelete='restrict',
        track_visibility='onchange', index=True, copy=False,
        domain="['|', ('team_ids', '=', False), ('team_ids', '=', team_id)]",
        group_expand='_read_group_stage_ids', default=lambda self: self._default_stage_id())

    def _read_group_stage_ids(self, stages, domain, order):
        team_id = self._context.get('default_team_id')
        if team_id:
            search_domain = [
                '|', ('id', 'in', stages.ids), '|', ('team_ids', '=', False),
                ('team_ids', 'in', [team_id])]
        else:
            search_domain = ['|', ('id', 'in', stages.ids), ('team_ids', '=', False)]
        # perform search
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)
