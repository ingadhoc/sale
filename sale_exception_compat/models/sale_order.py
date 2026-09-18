from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _exception_blocked_confirmation(self):
        """Undo everything the confirmation did and show the exception popup."""
        exception_map = {sale.id: sale.exception_ids.ids for sale in self}
        self.env.cr.rollback()
        # The rollback undoes the database writes but leaves the cache dirty,
        # so the next flush would write them back.
        self.env.invalidate_all()
        # Orders created in the transaction we just rolled back are gone.
        for sale in self.exists():
            sale.write({"exception_ids": [(6, 0, exception_map.get(sale.id, []))]})
        if not self.env.company.sale_exception_show_popup:
            return
        return self._popup_exceptions()

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
