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
        # Redefinimos método para que obtenga facturas en borrador.
        if not self.ids:
            self.debit = False
            self.credit = False
            return

        query = self.env["account.move.line"]._where_calc(
            [("parent_state", "=", "posted"), ("company_id", "child_of", self.env.company.root_id.id)]
        )
        self.env["account.move.line"].flush_model(
            ["account_id", "amount_residual", "company_id", "parent_state", "partner_id", "reconciled"]
        )
        self.env["account.account"].flush_model(["account_type"])

        sql = SQL(
            """
            SELECT account_move_line.partner_id, a.account_type, SUM(account_move_line.amount_residual)
            FROM %s
            LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
            WHERE a.account_type IN ('asset_receivable','liability_payable')
            AND account_move_line.partner_id IN %s
            AND account_move_line.reconciled IS NOT TRUE
            AND %s
            GROUP BY account_move_line.partner_id, a.account_type
            """,
            query.from_clause,
            tuple(self.ids),
            query.where_clause or SQL("TRUE"),
        )

        credit_map = {}
        debit_map = {}

        for pid, account_type, val in self.env.execute_query(sql):
            if account_type == "asset_receivable":
                credit_map[pid] = val
            elif account_type == "liability_payable":
                debit_map[pid] = -val

        draft_moves = self.env["account.move"].search(
            [
                ("state", "=", "draft"),
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("partner_id", "in", self.ids),
                ("company_id", "child_of", self.env.company.root_id.id),
            ]
        )
        for move in draft_moves:
            pid = move.partner_id.id
            credit_map[pid] = credit_map.get(pid, 0.0) + move.amount_total_signed

        for partner in self:
            partner.credit = credit_map.get(partner.id, 0.0)
            partner.debit = debit_map.get(partner.id, 0.0)
