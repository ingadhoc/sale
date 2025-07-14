##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class ResPartner(models.Model):
    _inherit = "res.partner"

    # credit_with_confirmed_orders = fields.Monetary(
    #     compute="_compute_credit_with_confirmed_orders",
    #     string="Credit Taken",
    #     help="Total amount this customer owes you (including not invoiced confirmed sale orders and draft invoices).",
    #     groups="account.group_account_invoice,account.group_account_readonly",
    # )
    user_credit_config = fields.Boolean(compute="_compute_user_credit_config")

    @api.depends_context("uid")
    def _compute_user_credit_config(self):
        self.user_credit_config = self.env.user.has_group("sale_exception_credit_limit.credit_config")

    def write(self, vals):
        """Si esta constraint trae dolores de cabeza la podemos sacar ya que este "bache" de seguridad esta en muchos
        lugares aún mas criticos. es un problema del ORM donde mucho se protege a nivel vista"""
        if "credit_limit" in vals or "use_partner_credit_limit" in vals:
            for record in self:
                if not self.env.user.has_group("sale_exception_credit_limit.credit_config"):
                    new_credit_limit = vals.get("credit_limit", record.credit_limit)
                    if not record.parent_id or new_credit_limit != record.parent_id.credit_limit:
                        raise ValidationError(
                            "People without Credit limit Configuration Rights cannot modify credit limit parameters"
                        )
        return super().write(vals)

    def _credit_debit_get(self):
        super()._credit_debit_get()
        credit_map = {
            res['partner_id'][0]: res['amount_total_signed']
            for res in self.env['account.move'].read_group(
                [
                    ("state", "=", "draft"),
                    ("move_type", "in", ["out_invoice", "out_refund"]),
                    ("partner_id", "in", self.ids),
                    ("company_id", "child_of", self.env.company.root_id.id),
                ],
                ["amount_total_signed"],
                ["partner_id"]
            ) if res['partner_id']
        }
        for partner in self:
            partner.credit = partner.credit + credit_map.get(partner.id, 0.0)
