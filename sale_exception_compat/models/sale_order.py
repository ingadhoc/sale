from odoo import models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import config


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _exception_blocked_confirmation(self):
        """Undo everything the confirmation did and show the exception popup."""
        exception_map = {sale.id: sale.exception_ids.ids for sale in self}
        # Tests forbid rolling back the test cursor.
        if not config["test_enable"]:
            self.env.cr.rollback()
        # The rollback undoes the database writes but leaves the cache dirty,
        # so the next flush would write them back.
        self.env.invalidate_all()
        # Any caller other than the confirm button would keep running on the
        # rolled-back transaction, so it has to stop here. It raises before the
        # write below because the exception would roll that write back anyway.
        if not self._called_from_confirm_button():
            exception_ids = {rule_id for rule_ids in exception_map.values() for rule_id in rule_ids}
            raise ValidationError("\n".join(self.env["exception.rule"].browse(exception_ids).mapped("name")))
        # Orders created in the transaction we just rolled back are gone.
        for sale in self.exists():
            sale.write({"exception_ids": [(6, 0, exception_map.get(sale.id, []))]})
        if not self.env.company.sale_exception_show_popup:
            return
        return self._popup_exceptions()

    def _called_from_confirm_button(self):
        # A test can force either flow; by default tests expect the popup.
        forced = self.env.context.get("sale_exception_from_button")
        if forced is not None:
            return forced
        if config["test_enable"]:
            return True
        if not request:
            return False
        # params is set by the dispatcher, so it may not be there yet.
        params = getattr(request, "params", None) or {}
        return (params.get("model"), params.get("method")) == (
            self._name,
            "action_confirm",
        )

    def action_confirm(self):
        if self.detect_exceptions():
            return self._exception_blocked_confirmation()
        return super().action_confirm()

    def _register_hook(self):
        # Exceptions must be detected before any other module runs its own
        # action_confirm: modules with no dependency between them are ordered
        # by installation order, so an override acting before its super() may
        # run first. Patching the resolved method puts the detection outermost.
        ModelClass = self.env.registry["sale.order"]
        original_action_confirm = ModelClass.action_confirm

        def patched_action_confirm(self):
            if self.detect_exceptions():
                return self._exception_blocked_confirmation()
            return patched_action_confirm.origin(self)

        patched_action_confirm.origin = original_action_confirm
        ModelClass.action_confirm = patched_action_confirm
        return super()._register_hook()
