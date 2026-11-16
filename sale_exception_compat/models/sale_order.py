from markupsafe import Markup
from odoo import models
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

    def _validate_order(self):
        # Portal signature and eCommerce write on the order right before this
        # call and the rollback would discard those writes: leave the blocked
        # orders unconfirmed instead, as OCA/sale-workflow#4600 does.
        self.detect_exceptions()
        blocked = self.filtered(lambda o: o._must_raise_exception_after_detection())
        for order in blocked:
            order.message_post(
                body=Markup("{}{}").format(
                    self.env._("The order was not confirmed because of these exceptions:"),
                    Markup(order.exceptions_summary or ""),
                ),
                subtype_xmlid="mail.mt_note",
            )
        to_confirm = self - blocked
        if to_confirm:
            return super(SaleOrder, to_confirm)._validate_order()

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
