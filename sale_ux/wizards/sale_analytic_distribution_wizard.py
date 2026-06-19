##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class SaleOrderAnalyticWizard(models.TransientModel):
    _name = "sale.order.analytic.wizard"
    _description = "Set Analytic Account on Sale Order Lines"

    plan_id = fields.Many2one(
        "account.analytic.plan",
        string="Analytic Plan",
        default=lambda self: self._default_plan_id(),
        help="Plan used when creating a new analytic account from this wizard.",
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        required=True,
        help="Analytic account that will be assigned (at 100%) to the selected lines.",
    )
    select_all = fields.Boolean(
        help="Check or uncheck every line at once.",
    )
    line_ids = fields.One2many(
        "sale.order.analytic.wizard.line",
        "wizard_id",
        string="Lines",
    )

    @api.model
    def _default_plan_id(self):
        return self.env["account.analytic.plan"].search([], limit=1)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "line_ids" in fields_list:
            active_ids = self.env.context.get("active_ids") or (
                [self.env.context["active_id"]] if self.env.context.get("active_id") else []
            )
            orders = self.env["sale.order"].browse(active_ids).exists()
            sale_lines = orders.order_line.filtered(lambda l: not l.display_type)
            res["line_ids"] = [(0, 0, {"sale_line_id": line.id, "selected": True}) for line in sale_lines]
        return res

    @api.onchange("select_all")
    def _onchange_select_all(self):
        for line in self.line_ids:
            line.selected = self.select_all

    def action_apply(self):
        self.ensure_one()
        lines_to_set = self.line_ids.filtered("selected").mapped("sale_line_id")
        # full replace: the chosen account is set at 100% (overrides any previous distribution)
        lines_to_set.write({"analytic_distribution": {str(self.analytic_account_id.id): 100}})
        return {"type": "ir.actions.act_window_close"}


class SaleOrderAnalyticWizardLine(models.TransientModel):
    _name = "sale.order.analytic.wizard.line"
    _description = "Analytic Account Wizard Line"

    wizard_id = fields.Many2one(
        "sale.order.analytic.wizard",
        required=True,
        ondelete="cascade",
    )
    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Sale Order Line",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean("Apply", default=True)
    order_id = fields.Many2one(related="sale_line_id.order_id", string="Order")
    product_id = fields.Many2one(related="sale_line_id.product_id", string="Product")
    name = fields.Text(related="sale_line_id.name", string="Description")
    current_analytic = fields.Char(
        compute="_compute_current_analytic",
    )

    @api.depends("sale_line_id.analytic_distribution")
    def _compute_current_analytic(self):
        for line in self:
            distribution = line.sale_line_id.analytic_distribution or {}
            account_ids = []
            for key in distribution:
                account_ids += [int(i) for i in str(key).split(",") if i]
            accounts = self.env["account.analytic.account"].browse(account_ids).exists()
            line.current_analytic = ", ".join(accounts.mapped("display_name"))
