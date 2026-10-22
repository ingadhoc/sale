import base64
import io
import os
import re

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged
from odoo.tools import file_path
from PIL import Image

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestReadmeFeatures(SaleUxCommon):
    """One test per feature of the README that no other test covers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.salesman = new_test_user(cls.env, login="readme_salesman", groups="sales_team.group_sale_salesman")

    def _arch(self, model, view_type, user=None, view_id=None):
        records = self.env[model].with_user(user) if user else self.env[model]
        return records.get_view(view_id=view_id, view_type=view_type)["arch"]

    def _user_with_group(self, login, *xmlids):
        return new_test_user(self.env, login=login, groups=",".join(("sales_team.group_sale_salesman", *xmlids)))

    def test_quotations_menu_is_hidden(self):
        self.assertFalse(self.env.ref("sale.menu_sale_quotations").active)

    def test_orders_action_shows_every_state(self):
        action = self.env.ref("sale.action_orders")

        self.assertIn(action.domain, ("[]", False))
        self.assertIn(action.context, ("{}", False))

    def test_order_search_view_has_the_ux_filters(self):
        arch = self._arch("sale.order", "search", view_id=self.env.ref("sale.sale_order_view_search_inherit_sale").id)

        for name in ("draft", "sales", "invoiced", "create_date"):
            self.assertIn('name="%s"' % name, arch)

    def test_customer_reference_is_shown_in_list_and_form_only_with_the_setting(self):
        user_with_setting = self._user_with_group("readme_ref_user", "sale_ux.group_reference_on_tree_and_main_form")

        list_with = self._arch("sale.order", "list", user_with_setting).count('name="client_order_ref"')
        list_without = self._arch("sale.order", "list", self.salesman).count('name="client_order_ref"')
        form_with = self._arch("sale.order", "form", user_with_setting)
        form_without = self._arch("sale.order", "form", self.salesman)

        self.assertGreater(list_with, list_without)
        # with the setting the field moves to the main section, before the order details
        # group (validity date); without it it stays in the "Other Info" tab, after it
        marker = 'name="validity_date"'
        field = 'name="client_order_ref"'
        self.assertLess(form_with.index(field), form_with.index(marker))
        self.assertGreater(form_without.index(field), form_without.index(marker))

    def test_sale_order_lines_menu_is_under_orders(self):
        menu = self.env.ref("sale_ux.menu_sale_order")

        self.assertEqual(menu.parent_id, self.env.ref("sale.sale_order_menu"))
        self.assertEqual(menu.action, self.env.ref("sale_ux.action_sale_order_line_usability_tree"))

    def test_sale_order_lines_list_has_the_extra_fields(self):
        arch = self._arch("sale.order.line", "list", view_id=self.env.ref("sale_ux.sale_order_line_usability_tree").id)

        for name in ("team_id", "categ_id", "qty_invoiced", "salesman_id"):
            self.assertIn('name="%s"' % name, arch)

    def test_order_form_renames_line_subtotal_and_total(self):
        arch = self._arch("sale.order", "form")

        self.assertIn('string="Subtotal"', arch)
        self.assertIn('string="Total"', arch)

    def test_force_invoiced_status_field_is_only_for_technical_features(self):
        # in Odoo 20 the technical features group only applies in debug mode, so the
        # restriction is checked on the view that declares the field
        view = self.env.ref("sale_ux.view_order_form")

        self.assertRegex(view.arch_db, r'<field name="force_invoiced_status"[^>]*groups="base.group_no_one"')
        regular = re.search(
            r'<field name="force_invoiced_status"[^>]*>', self._arch("sale.order", "form", self.salesman)
        )
        self.assertIn('invisible="1"', regular.group(0))

    def test_internal_notes_field_is_in_the_order_form(self):
        self.assertIn('name="internal_notes"', self._arch("sale.order", "form"))

    def test_order_list_has_amount_to_invoice_and_uninvoiced(self):
        arch = self._arch("sale.order", "list")

        self.assertIn('name="amount_uninvoiced"', arch)
        self.assertIn('name="amount_to_invoice"', arch)

    def test_lists_of_the_orders_and_quotations_menus_have_the_optional_columns(self):
        """In 20 these menus use lists that do not inherit from sale.view_order_tree."""
        for xmlid in ("sale.sale_order_list_with_dashboard", "sale.view_quotation_tree_with_onboarding"):
            arch = self._arch("sale.order", "list", view_id=self.env.ref(xmlid).id)
            for column in ("amount_uninvoiced", "amount_to_invoice", "create_date"):
                self.assertIn(f'name="{column}"', arch, f"{column} is missing in {xmlid}")

    def test_update_prices_button_is_visible_to_salesman_without_pricelists(self):
        self.assertIn('name="action_update_prices"', self._arch("sale.order", "form", self.salesman))

    def test_effective_pricelist_is_readonly_in_the_partner_form(self):
        user = self._user_with_group("readme_pricelist_user", "product.group_product_pricelist")

        arch = self._arch("res.partner", "form", user)
        field = re.search(r'<field name="property_product_pricelist"[^>]*>', arch)

        self.assertTrue(field, "the partner form has no effective pricelist field")
        self.assertRegex(field.group(0), r'readonly="(True|1)"')

    def test_pricelist_with_confirmed_sales_cannot_be_deleted(self):
        pricelist = self.env["product.pricelist"].create({"name": "Sale UX confirmed pricelist"})
        order = self._create_sale_order(pricelist_id=pricelist.id)
        order.action_confirm()

        with self.assertRaisesRegex(UserError, "cannot be deleted"):
            pricelist.unlink()

    def test_product_form_has_the_all_pricelists_tab(self):
        user = self._user_with_group("readme_prices_user", "product.group_product_pricelist")

        arch = self._arch("product.template", "form", user)

        self.assertIn('name="pricelist_ids"', arch)
        self.assertRegex(arch, r'<field name="fixed_pricelist_rule_ids"[^>]*invisible="(True|1)"')

    def test_analytic_wizard_assigns_the_account_to_the_selected_lines_only(self):
        order = self._create_sale_order(
            order_line=[
                Command.create({"product_id": self.product.id, "product_uom_qty": 1, "price_unit": 10.0}),
                Command.create({"product_id": self.product.id, "product_uom_qty": 1, "price_unit": 20.0}),
                Command.create({"display_type": "line_section", "name": "Section"}),
            ]
        )
        plan = self.env["account.analytic.plan"].create({"name": "Sale UX plan"})
        account = self.env["account.analytic.account"].create({"name": "Sale UX account", "plan_id": plan.id})
        wizard = (
            self.env["sale.order.analytic.wizard"]
            .with_context(active_ids=order.ids, active_model="sale.order")
            .create({"analytic_account_id": account.id})
        )
        self.assertEqual(len(wizard.line_ids), 2, "sections and notes are not listed")
        wizard.line_ids[1].selected = False

        wizard.action_apply()

        first, second = order.order_line.filtered(lambda line: not line.display_type)
        self.assertEqual(first.analytic_distribution, {str(account.id): 100})
        self.assertFalse(second.analytic_distribution)

    def test_quotation_report_shows_the_product_image_with_the_chosen_size(self):
        image = io.BytesIO()
        Image.new("RGB", (600, 600), (200, 30, 30)).save(image, format="JPEG")
        self.product.write({"image_1920": base64.b64encode(image.getvalue()).decode()})
        order = self._create_sale_order()
        render = (
            lambda: self.env["ir.actions.report"]
            ._render_qweb_html("sale.action_report_saleorder", order.ids)[0]
            .decode()
        )

        self.env.company.display_product_images_on_so = False
        self.assertNotIn("max-width: 50px", render())

        self.env.company.display_product_images_on_so = True
        for size, pixels in (("128_50", 50), ("256_100", 100), ("512_150", 150)):
            self.IrConfig.set_str("sale_ux.product_image_size", size)
            html = render()
            self.assertIn("max-width: %spx" % pixels, html, size)
            self.assertIn("data:image/", html, size)

    def test_auto_select_all_documents_selects_the_available_quotation_documents(self):
        order = self._create_sale_order()
        if not order.available_quotation_document_ids:
            self.skipTest("no quotation document available to select")
        self.IrConfig.set_bool("sale_ux.auto_select_all_documents", False)
        order.get_update_included_pdf_params()
        self.assertFalse(order.quotation_document_ids)

        self.IrConfig.set_bool("sale_ux.auto_select_all_documents", True)
        order.get_update_included_pdf_params()

        self.assertEqual(order.quotation_document_ids, order.available_quotation_document_ids)

    def test_portal_shows_the_delivery_date_and_the_payment_term_name(self):
        self.env.user.group_ids |= self.env.ref("sale_ux.group_delivery_date_on_report_online")
        term = self.env["account.payment.term"].create(
            {
                "name": "Sale UX 15 days",
                "line_ids": [Command.create({"value": "percent", "value_amount": 100, "nb_days": 15})],
            }
        )
        order = self._create_sale_order(
            payment_term_id=term.id, commitment_date="2030-01-15 12:00:00", note="<p>Terms</p>"
        )

        html = self.env["ir.qweb"]._render(
            "sale.sale_order_portal_content",
            {
                "sale_order": order,
                "report_type": "html",
                "resize_to_attachment": False,
                "backend_url": "",
                "res_company": order.company_id,
                "user": self.env.user,
            },
        )

        self.assertIn("Delivery:", str(html))
        self.assertIn("Sale UX 15 days", str(html))

    def test_import_templates_exist_for_customers_and_products(self):
        templates = self.env["res.partner"].with_context(res_partner_search_mode="customer").get_import_templates()
        templates += (
            self.env["product.template"].with_context(sale_multi_pricelist_product_template=True).get_import_templates()
        )

        self.assertEqual(len(templates), 2)
        for template in templates:
            self.assertTrue(os.path.exists(file_path(template["template"].lstrip("/"))), template["label"])

    def test_fixed_down_payment_with_price_included_taxes_invoices_the_amount_asked(self):
        tax = self.env["account.tax"].create(
            {
                "name": "Sale UX 21% included down payment",
                "amount": 21,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "price_include_override": "tax_included",
            }
        )
        product = self.env["product.product"].create(
            {"name": "Sale UX taxed product", "type": "consu", "list_price": 121.0, "taxes_id": [Command.set([tax.id])]}
        )
        order = self._create_sale_order(order_line=[Command.create({"product_id": product.id, "product_uom_qty": 1})])
        order.action_confirm()

        self.env["sale.advance.payment.inv"].with_context(active_ids=order.ids, active_model="sale.order").create(
            {"advance_payment_method": "fixed", "fixed_amount": 50.0}
        ).create_invoices()

        self.assertEqual(order.invoice_ids.amount_total, 50.0)

    def test_online_quotation_shows_the_product_image_only_with_the_company_setting(self):
        image = io.BytesIO()
        Image.new("RGB", (300, 300), (30, 30, 200)).save(image, format="JPEG")
        self.product.write({"image_1920": base64.b64encode(image.getvalue()).decode()})
        order = self._create_sale_order()

        def render():
            return str(
                self.env["ir.qweb"]._render(
                    "sale.sale_order_portal_content",
                    {
                        "sale_order": order,
                        "report_type": "html",
                        "resize_to_attachment": False,
                        "backend_url": "",
                        "res_company": order.company_id,
                        "user": self.env.user,
                    },
                )
            )

        # the online quotation uses the native image (image_128), the size selector only applies to the PDF
        self.env.company.display_product_images_on_so = False
        self.assertNotIn("o_sale_portal_product_image", render())
        self.env.company.display_product_images_on_so = True
        self.assertIn("o_sale_portal_product_image", render())

    def test_product_prices_tab_lists_pricelists_without_rules_for_the_product(self):
        self.env["product.pricelist"].create({"name": "Sale UX pricelist without rules", "show_products": True})
        template = self.env["product.template"].create({"name": "Sale UX template", "list_price": 40.0})

        prices = {pricelist.name: pricelist.price for pricelist in template.pricelist_ids}

        self.assertEqual(prices["Sale UX pricelist without rules"], 40.0)

    def test_sale_history_button_is_hidden_on_lines_without_product(self):
        arch = self._arch("sale.order", "form")

        button = re.search(r'<button name="action_sale_history"[^>]*>', arch)

        self.assertTrue(button)
        self.assertIn('invisible="not product_id"', button.group(0))
