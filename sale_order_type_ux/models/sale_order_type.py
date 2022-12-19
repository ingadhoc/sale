from odoo import models, fields


class SaleOrderTypology(models.Model):

    _inherit = 'sale.order.type'
    _order = "sequence asc"

    sequence = fields.Integer(
        'Sequence',
        required=True,
        default=10,
    )

    team_id = fields.Many2one(
        'crm.team',
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id),]",
    )

    active = fields.Boolean(
        default=True, help="Set active to false to hide the type of sale without removing it.")

    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        string='Fiscal Position',
        check_company=True,
        help='If you choose a fiscal position then this fiscal positioon would be used as default instead of the '
        'automatically detected or setted on the partner')

    journal_id = fields.Many2one(
        domain="[('type', '=', 'sale')]",
        check_company=False)
