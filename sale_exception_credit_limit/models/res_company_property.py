##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class ResCompanyProperty(models.Model):
    _inherit = "res.company.property"

    property_credit_limit = fields.Float(
        string="Credit Limit",
        compute="_compute_property_credit_limit",
        inverse="_inverse_property_credit_limit",
    )

    @api.depends("property_field")
    def _compute_property_credit_limit(self):
        for record in self:
            if record.property_field == "credit_limit":
                record.property_credit_limit = record._get_property_value()
            else:
                record.property_credit_limit = 0.0

    def _inverse_property_credit_limit(self):
        for rec in self:
            rec._set_property_value(rec.property_credit_limit)
