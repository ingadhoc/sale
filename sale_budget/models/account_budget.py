from odoo import models


class AccountBudget(models.Model):
    _inherit = "crossovered.budget"

    def copy_and_link_to_so(self):
        sale = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if not sale or sale._name != 'sale.order':
            # TODO devolver un raise
            return
        if not sale.analytic_account_id:
            sale.analytic_account_id = sale.analytic_account_id.create({
                'name': sale.name,
                'partner_id': sale.partner_invoice_id.id,
                # TODO crear un nuevo plan para este cliente
                'plan_id': 1,
            })
        self.copy()
        for line in self.crossovered_budget_line:
            line.analytic_account_id = sale.analytic_account_id.id
        return
