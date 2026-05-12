from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class SaleOrderTypology(models.Model):
    _inherit = "sale.order.type"
    _order = "sequence asc"

    sequence = fields.Integer(
        required=True,
        default=10,
    )

    team_id = fields.Many2one(
        "crm.team",
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id),]",
        help="This field will not be considered for sales coming from eCommerce. You should configure it directly in Settings > Website.",
    )

    active = fields.Boolean(default=True, help="Set active to false to hide the type of sale without removing it.")

    fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        check_company=True,
        help="If you choose a fiscal position then this fiscal positioon would be used as default instead of the "
        "automatically detected or setted on the partner",
    )

    warehouse_id = fields.Many2one(
        help="This field will not be considered for sales coming from eCommerce. You should configure it directly in Settings > Website."
    )

    company_id = fields.Many2one(
        help="This field will not be considered for sales coming from eCommerce. You should configure it directly in Settings > Website."
    )

    pricelist_id = fields.Many2one(
        help="This field will not be considered for sales coming from eCommerce. You should configure it directly in Settings > Website."
    )
    invoice_company_id = fields.Many2one(
        "res.company",
        string="Invoice Company",
        domain="[('id', 'child_of', company_id)]",
        compute="_compute_invoice_company_id",
        store=True,
        readonly=False,
        precompute=True,
    )
    journal_domain = fields.Binary(compute="_compute_journal_domain")
    journal_id = fields.Many2one(
        "account.journal", string="Invoice Journal", domain="journal_domain", check_company=False
    )
    invoice_count = fields.Integer(
        compute="_compute_invoice_count",
        help="Number of invoices created from sales orders of this type. This field is used to determine whether the modification of a sale order type is not recommended.",
    )
    so_count = fields.Integer(
        compute="_compute_so_count",
        help="Number of sales orders created from this type. This field is used to determine whether the modification of a sale order type is not recommended.",
    )

    @api.depends("company_id")
    def _compute_invoice_company_id(self):
        for rec in self:
            rec.invoice_company_id = rec.company_id

    @api.depends("invoice_company_id")
    def _compute_journal_domain(self):
        for rec in self:
            rec.journal_domain = Domain(
                rec.env["account.journal"]._check_company_domain(rec.invoice_company_id)
            ) & Domain("type", "=", "sale")

    @api.constrains("invoice_company_id", "journal_id")
    def _check_journal_company(self):
        for rec in self:
            if rec.journal_id and rec.journal_id not in rec.env["account.journal"].search(rec.journal_domain):
                raise ValidationError("The selected 'Invoice Journal' does not belong to the selected invoice company.")

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = self.env["account.move"].search_count([("sale_type_id", "=", rec.id)])

    def _compute_so_count(self):
        for rec in self:
            rec.so_count = self.env["sale.order"].search_count([("type_id", "=", rec.id)])
