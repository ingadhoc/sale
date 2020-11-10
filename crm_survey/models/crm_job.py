from odoo import api, fields, models


class Job(models.Model):
    _inherit = "crm.team"

    survey_id = fields.Many2one(
        'survey.survey', "Interview Form",
        help="Choose an interview form")

    @api.multi
    def action_print_survey(self):
        return self.survey_id.action_print_survey()
