##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestSaleOrderAddressTracking(SaleUxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # the common setup disables mail, but tracking is exactly what we test here
        cls.tracked_env = cls.env(
            context={key: value for key, value in cls.env.context.items() if key not in DISABLED_MAIL_CONTEXT}
        )
        # an unrelated company, like the one the user picks in the address selector
        cls.other_company = cls.env["res.partner"].create(
            {
                "name": "Sale UX Other Company",
                "property_account_receivable_id": cls.receivable_account.id,
                "property_account_payable_id": cls.payable_account.id,
            }
        )

    def _flush_tracking(self):
        """Tracking messages are only written on precommit."""
        self.env.flush_all()
        self.env.cr.flush()

    def _new_tracked_order(self):
        order = self._create_sale_order().with_env(self.tracked_env)
        # the order was created with tracking disabled, drop that pending state
        self._flush_tracking()
        return order

    def _tracked_values(self, order, field_name):
        self._flush_tracking()
        trackings = order.message_ids.sudo().tracking_value_ids
        return trackings.filtered(lambda tracking: tracking.field_id.name == field_name)

    def test_invoice_address_change_is_tracked(self):
        order = self._new_tracked_order()
        self.assertEqual(order.partner_invoice_id, self.partner_a)

        order.write({"partner_invoice_id": self.other_company.id})

        tracked = self._tracked_values(order, "partner_invoice_id")
        self.assertEqual(len(tracked), 1)
        self.assertEqual(tracked.old_value_char, self.partner_a.display_name)
        self.assertEqual(tracked.new_value_char, self.other_company.display_name)

    def test_delivery_address_change_is_tracked(self):
        order = self._new_tracked_order()
        self.assertEqual(order.partner_shipping_id, self.partner_a)

        order.write({"partner_shipping_id": self.other_company.id})

        tracked = self._tracked_values(order, "partner_shipping_id")
        self.assertEqual(len(tracked), 1)
        self.assertEqual(tracked.old_value_char, self.partner_a.display_name)
        self.assertEqual(tracked.new_value_char, self.other_company.display_name)

    def test_customer_change_tracks_the_three_addresses(self):
        """Both addresses are stored computes: the recompute must be tracked too."""
        order = self._new_tracked_order()

        order.write({"partner_id": self.partner_b.id})

        for field_name in ("partner_id", "partner_invoice_id", "partner_shipping_id"):
            tracked = self._tracked_values(order, field_name)
            self.assertEqual(len(tracked), 1, "%s was not tracked" % field_name)
            self.assertEqual(tracked.old_value_char, self.partner_a.display_name)
            self.assertEqual(tracked.new_value_char, self.partner_b.display_name)

    def test_address_change_posts_a_chatter_message(self):
        order = self._new_tracked_order()
        messages_before = order.message_ids

        order.write({"partner_invoice_id": self.other_company.id})
        self._flush_tracking()

        new_messages = order.message_ids - messages_before
        self.assertTrue(new_messages, "no message was posted in the chatter")
        self.assertIn(
            "partner_invoice_id",
            new_messages.sudo().tracking_value_ids.mapped("field_id.name"),
        )
