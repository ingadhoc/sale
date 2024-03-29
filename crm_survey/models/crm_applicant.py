# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Applicant(models.Model):
    _inherit = "crm.lead"

    survey_id = fields.Many2one(
        'survey.survey', related='team_id.survey_id', string="Survey",
        readonly=False)
    response_id = fields.Many2one(
        'survey.user_input', "Response", ondelete="set null")

    def action_start_survey(self):
        self.ensure_one()
        # create a response and link it to this applicant
        if not self.response_id:
            # use link as type in order to avoid deletion of records
            # that they wasn't started yet made by 'do_clean_emptys' method
            response = self.survey_id.with_context(default_input_type="link")._create_answer(partner=self.partner_id)
            self.response_id = response.id
        else:
            response = self.response_id
        # grab the token of the response and start surveying
        return self.survey_id.with_context(
            survey_token=response.access_token).action_start_survey(response)

    def action_print_survey(self):
        """ If response is available then print"""
        self.ensure_one()
        if not self.response_id:
            return self.survey_id.action_print_survey()
        else:
            response = self.response_id
            return self.survey_id.with_context(
                survey_token=response.access_token).action_print_survey(response)
