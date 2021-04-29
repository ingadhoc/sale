from odoo import fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'


    # TODO remove in 15
    def action_post(self):
        #inherit of the function from account.move to validate a new tax and the priceunit of a downpayment
        res = super(AccountMove, self).action_post()
        line_ids = self.mapped('line_ids').filtered(lambda line: line.sale_line_ids.is_downpayment)
        for line in line_ids:
            try:
                line.sale_line_ids.tax_id = line.tax_ids
                if all(line.tax_ids.mapped('price_include')):
                    line.sale_line_ids.price_unit = line.price_unit
                else:
                    #To keep positive amount on the sale order and to have the right price for the invoice
                    #We need the - before our untaxed_amount_to_invoice
                    line.sale_line_ids.price_unit = -line.sale_line_ids.untaxed_amount_to_invoice
                    # we add to block the SO when the price of the downpayment is zero.
                    # TODO v15 we keep this in inherit method
                    if line.sale_line_ids.price_unit <= 0.0:
                        line.sale_line_ids.order_id.state = 'done'
            except UserError:
                # a UserError here means the SO was locked, which prevents changing the taxes
                # just ignore the error - this is a nice to have feature and should not be blocking
                pass
        return res
