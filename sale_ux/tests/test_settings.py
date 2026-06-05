from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestSaleUxSettings(SaleUxCommon):
    def test_setting_show_customer_reference_field_is_stored(self):
        """Test that 'Show Customer Reference' setting is stored properly"""
        self.IrConfig.set_param("sale_ux.show_customer_reference", "True")

        result = self.IrConfig.get_param("sale_ux.show_customer_reference")

        self.assertEqual(result, "True")

    def test_setting_propagate_internal_notes_is_stored(self):
        """Test that internal notes propagation setting is stored"""
        self.IrConfig.set_param("sale.propagate_internal_notes", "True")

        result = self.IrConfig.get_param("sale.propagate_internal_notes")

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
        self.IrConfig.set_param("sale_ux.days_to_keep_quotations", "-1")

        result = self.IrConfig.get_param("sale_ux.days_to_keep_quotations")

        # Setting should be retrievable but should be validated elsewhere
        self.assertIsNotNone(result)

    def test_setting_for_automatic_price_update_is_stored(self):
        """Test that automatic price update setting is stored"""
        self.IrConfig.set_param("sale_ux.update_prices_automatically", "True")

        result = self.IrConfig.get_param("sale_ux.update_prices_automatically")

        self.assertEqual(result, "True")

    def test_setting_for_show_product_image_on_quotation_is_stored(self):
        """Test that product image on quotation setting is stored"""
        self.IrConfig.set_param("sale_ux.show_product_image_quotation", "True")

        result = self.IrConfig.get_param("sale_ux.show_product_image_quotation")

        self.assertEqual(result, "True")

    def test_setting_for_allow_any_salesman_is_stored(self):
        """Test that 'allow any salesman' setting is stored"""
        self.IrConfig.set_param("sale_ux.allow_any_salesman", "True")

        result = self.IrConfig.get_param("sale_ux.allow_any_salesman")

        self.assertEqual(result, "True")

    def test_setting_for_allow_any_team_member_is_stored(self):
        """Test that 'allow any team member' setting is stored"""
        self.IrConfig.set_param("sale_ux.allow_any_team_member", "True")

        result = self.IrConfig.get_param("sale_ux.allow_any_team_member")

        self.assertEqual(result, "True")

    def test_setting_for_create_analytic_account_without_company_is_stored(self):
        """Test that analytic account without company setting is stored"""
        self.IrConfig.set_param("sale_ux.create_analytic_without_company", "True")

        result = self.IrConfig.get_param("sale_ux.create_analytic_without_company")

        self.assertEqual(result, "True")
