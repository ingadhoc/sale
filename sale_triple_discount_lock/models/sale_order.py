from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _recompute_prices(self):
        # super() does 'discount = 0', and triple.discount.mixin.write() turns any
        # write of 'discount' into discount1 and zeroes discount2 and discount3.
        # So we save them before and write them back, with the pricelist discount
        # in discount1.
        saved = {line.id: (line.discount2, line.discount3) for line in self.order_line}

        super()._recompute_prices()

        # discount1 is what super()'s compute gives: the pricelist discount, plus
        # whatever else sits below it (a pack component discount, for instance).
        self.order_line.invalidate_recordset(["discount1"])
        for line in self.order_line:
            d2, d3 = saved[line.id]
            line.write({"discount1": line.discount1, "discount2": d2, "discount3": d3})
