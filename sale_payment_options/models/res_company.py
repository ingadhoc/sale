from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_payment_options_by_line = fields.Boolean(
        string="Discriminate Payment Options by Sale Line",
        help="Print the installment amounts under each sale order line instead of the "
        "payment options table of the whole order.",
    )
