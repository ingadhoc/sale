from odoo import fields, models


class QuotationDocument(models.Model):
    _inherit = "quotation.document"

    quotation_template_ids = fields.Many2many(
        groups="sales_team.group_sale_salesman,portal_sale_distributor.group_portal_backend_distributor"
    )
