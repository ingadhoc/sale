from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"
    _name = "sale.order"

    def sale_check_exception(self):
        super().sale_check_exception()
        for rec in self:
            if rec.state == "draft":
                if rec.detect_exceptions():
                    return rec._popup_exceptions()
