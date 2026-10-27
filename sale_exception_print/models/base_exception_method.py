##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models

PRINT_EXCEPTION_MODELS = ["sale.order", "sale.order.line"]


class BaseExceptionMethod(models.AbstractModel):
    _inherit = "base.exception.method"

    def _is_print_exception_detection(self):
        return self.env.context.get("print_exceptions", False) and self._name in PRINT_EXCEPTION_MODELS

    def _rule_domain(self):
        """Filter exception.rules.
        By default, only the rules with the correct model
        will be used.
        """
        domain = super()._rule_domain()
        if self._is_print_exception_detection():
            domain += [("block_print", "=", True)]
        return domain

    def _must_raise_exception_after_detection(self):
        """While printing, only the rules that block printing stop the action."""
        if self._is_print_exception_detection():
            return bool(self._get_main_records().exception_ids.filtered("block_print"))
        return super()._must_raise_exception_after_detection()

    def _detect_exception_get_exc_class_values(self):
        """Tell the client handler that the exception comes from the print flow."""
        res = super()._detect_exception_get_exc_class_values()
        if self._is_print_exception_detection():
            res = dict(
                res,
                print_exception=True,
                record_ids=self._get_main_records().ids,
            )
        return res
