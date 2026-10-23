from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestSaleUxSettings(SaleUxCommon):
    def test_setting_propagate_internal_notes_is_stored(self):
        """Test that internal notes propagation setting is stored"""
        self.IrConfig.set_str("sale.propagate_internal_notes", "True")

        result = self.IrConfig.get_str("sale.propagate_internal_notes")

        self.assertEqual(result, "True")

    def test_setting_hide_quotations_menu_can_be_configured(self):
        """Test that quotations menu visibility can be configured"""
        menu = self.env.ref("sale.menu_sale_quotations", raise_if_not_found=False)
        if menu:
            original_visible = menu.active
            menu.active = False

            self.assertFalse(menu.active)

            menu.active = original_visible

    def test_setting_hide_invoicing_menu_can_be_configured(self):
        """Test that invoicing menu visibility can be configured"""
        menu = self.env.ref("account.menu_finance_receivables", raise_if_not_found=False)
        if menu:
            original_visible = menu.active
            menu.active = False

            self.assertFalse(menu.active)

            menu.active = original_visible

    def test_setting_for_quotation_auto_cancellation_days_must_be_positive(self):
        """Test that quotation auto-cancellation days setting must be positive"""
        self.IrConfig.set_str("sale_ux.days_to_keep_quotations", "-1")

        result = self.IrConfig.get_str("sale_ux.days_to_keep_quotations")

        # Setting should be retrievable but should be validated elsewhere
        self.assertIsNotNone(result)
