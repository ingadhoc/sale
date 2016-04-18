# -*- coding: utf-8 -*-
from openerp import models, api


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.multi
    def print_quotation(self):
        self.ensure_one()
        if self.detect_exceptions():
            return self._popup_exceptions()
        else:
            return super(sale_order, self).print_quotation()

    @api.multi
    def action_quotation_send(self):
        self.ensure_one()
        if self.detect_exceptions():
            return self._popup_exceptions()
        else:
            return super(sale_order, self).action_quotation_send()
