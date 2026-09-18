from odoo import models
from odoo.addons.base_exception.models.base_exception_method import BaseExceptionMethod
from odoo.fields import Command


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _detect_exceptions(self, rule):
        # Skip sale_exception's override, which writes through a second cursor.
        records = BaseExceptionMethod._detect_exceptions(self, rule)
        lines_to_remove_exception = (self - records).filtered(lambda line: rule.id in line.exception_ids.ids)
        lines_to_remove_exception.exception_ids = [Command.unlink(rule.id)]
        lines_to_add_exception = records.filtered(lambda line: rule.id not in line.exception_ids.ids)
        lines_to_add_exception.exception_ids = [Command.link(rule.id)]
        return records.mapped("order_id")
