import base64
import io

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import new_test_user, tagged
from PIL import Image

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestPartnerProductConfig(SaleUxCommon):
    def test_config_settings_store_sale_ux_parameters(self):
        settings = self.env["res.config.settings"].create(
            {
                "move_internal_notes": True,
                "move_note": False,
                "update_prices_automatically": True,
                "days_to_keep_quotations": 15,
            }
        )

        settings.set_values()
        values = settings.get_values()

        self.assertTrue(values["move_internal_notes"])
        self.assertFalse(values["move_note"])
        self.assertTrue(values["update_prices_automatically"])
        self.assertEqual(self.IrConfig.get_param("sale_ux.days_to_keep_quotations"), "15")

    def test_config_settings_days_to_keep_quotations_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.env["res.config.settings"].create({"days_to_keep_quotations": 0})

    def test_partner_without_specific_pricelist_keeps_dynamic_fallback(self):
        first_pricelist = self.env["product.pricelist"].search([], order="sequence", limit=1)
        partner = self.env["res.partner"].create(
            {
                "name": "Sale UX dynamic pricelist partner",
                "property_product_pricelist": first_pricelist.id,
            }
        )

        self.assertFalse(partner.specific_property_product_pricelist)

    def test_partner_explicit_pricelist_is_preserved_as_specific(self):
        self.env["product.pricelist"].create(
            {
                "name": "Sale UX default pricelist",
                "sequence": 1,
            }
        )
        specific_pricelist = self.env["product.pricelist"].create(
            {
                "name": "Sale UX specific pricelist",
                "sequence": 999,
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Sale UX fixed pricelist partner",
                "property_product_pricelist": specific_pricelist.id,
            }
        )

        self.assertEqual(partner.specific_property_product_pricelist, specific_pricelist)

    def test_only_packagings_without_packagings_has_no_available_uoms(self):
        template = self.env["product.template"].create(
            {
                "name": "Sale UX packaging product",
                "type": "consu",
                "uom_id": self.product_uom_unit.id,
            }
        )
        template.only_packagings = True

        self.assertFalse(template._get_available_uoms())

    def test_recompute_image_sale_order_without_products_returns_notification(self):
        action = self.env["product.template"].action_recompute_image_sale_order()

        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")

    def test_compute_image_sale_order_keeps_non_webp_image(self):
        image = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05"
            b"\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        template = self.env["product.template"].create(
            {
                "name": "Sale UX image product",
                "type": "consu",
                "image_1920": image,
            }
        )

        template._compute_image_sale_order()

        self.assertTrue(template.image_sale_order)

    def test_compute_image_sale_order_converts_webp_to_jpeg(self):
        image_stream = io.BytesIO()
        Image.new("RGBA", (1, 1), (0, 128, 255, 128)).save(image_stream, format="WEBP")
        self.IrConfig.set_param("sale_ux.product_image_size", "1920_50")
        template = self.env["product.template"].new(
            {
                "name": "Sale UX webp image product",
                "type": "consu",
                "image_1920": base64.b64encode(image_stream.getvalue()),
            }
        )

        template._compute_image_sale_order()

        self.assertTrue(base64.b64decode(template.image_sale_order).startswith(b"\xff\xd8"))

    def test_pricelist_computes_contextual_product_price(self):
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Sale UX visible pricelist",
                "show_products": True,
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "fixed",
                            "fixed_price": 42.0,
                        }
                    )
                ],
            }
        )

        pricelist.with_context(pricelist_product_id=self.product.id)._compute_price()

        self.assertEqual(pricelist.price, 42.0)

    def test_pricelist_without_context_computes_zero_price(self):
        pricelist = self.env["product.pricelist"].create({"name": "Sale UX no context"})

        pricelist._compute_price()

        self.assertEqual(pricelist.price, 0.0)

    def test_template_pricelist_context_computes_product_template_price(self):
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Sale UX template pricelist",
                "show_products": True,
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "fixed",
                            "fixed_price": 33.0,
                        }
                    )
                ],
            }
        )

        pricelist.with_context(pricelist_template_id=self.product.product_tmpl_id.id)._compute_price()

        self.assertEqual(pricelist.price, 33.0)

    def test_product_and_template_compute_visible_pricelists(self):
        visible_pricelist = self.env["product.pricelist"].create(
            {
                "name": "Sale UX visible product pricelist",
                "show_products": True,
            }
        )
        hidden_pricelist = self.env["product.pricelist"].create(
            {
                "name": "Sale UX hidden product pricelist",
                "show_products": False,
            }
        )

        self.product._compute_pricelist_ids()
        self.product.product_tmpl_id._compute_pricelist_ids()

        self.assertIn(visible_pricelist, self.product.pricelist_ids)
        self.assertNotIn(hidden_pricelist, self.product.pricelist_ids)
        self.assertIn(visible_pricelist, self.product.product_tmpl_id.pricelist_ids)
        self.assertNotIn(hidden_pricelist, self.product.product_tmpl_id.pricelist_ids)

    def test_pricelist_form_is_readonly_for_sales_user(self):
        sales_user = new_test_user(
            self.env,
            login="sale_ux_pricelist_sales_user",
            groups="sales_team.group_sale_salesman",
        )

        arch, _view = self.env["product.pricelist"].with_user(sales_user)._get_view(view_type="form")

        self.assertEqual(arch.xpath("//form")[0].get("edit"), "false")

    def test_fiscal_position_does_not_affect_prices_when_deduct_setting_false(self):
        """Test that fiscal positions don't affect prices when deduct_included_tax=False"""
        if "deduct_included_tax" not in self.env["account.fiscal.position"]._fields:
            self.skipTest("deduct_included_tax is provided by an optional dependency")

        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Test FP",
                "auto_apply": False,
                "deduct_included_tax": False,
            }
        )
        order = self._create_sale_order(
            fiscal_position_id=fiscal_position.id,
            partner_id=self.partner_a.id,
        )
        original_price = order.order_line[0].price_unit

        order._onchange_fiscal_position_id()

        self.assertEqual(order.order_line[0].price_unit, original_price)

    def test_config_setting_for_pdf_auto_selection_is_stored(self):
        """Test that PDF Quote Builder auto-selection setting is stored properly"""
        self.IrConfig.set_param("sale_ux.pdf_quote_auto_select", "True")

        result = self.IrConfig.get_param("sale_ux.pdf_quote_auto_select")

        self.assertEqual(result, "True")
