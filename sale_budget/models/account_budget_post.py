from odoo import fields, models


class AccountBudgetPost(models.Model):
    _inherit = "account.budget.post"

    # por como esta diseñado ahora se concatena producto con cuenta con un "and" pero según se necesite
    # y sea mas facil heredaarlo, podemos hacer que si o si se auno u otro (esa creo que es la mas facil para
    # resolver todo con herencia)
    product_ids = fields.Many2many('product.product', string='Products')

    def _check_account_ids(self, vals):
        if 'product_ids' in vals:
            product_ids = self.new({'product_ids': vals['product_ids']}, origin=self).product_ids
        else:
            product_ids = self.product_ids
        if product_ids:
            return
        else:
            # TODO deberiamos ver como mejorar mensaje de super para que diga cuentas o productos
            super()._check_account_ids(vals)
