from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import new_test_user, tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestPartnerProductConfig(SaleUxCommon):
    def test_config_settings_store_sale_ux_parameters(self):
        settings = self.env["res.config.settings"].create(
            {
                "move_internal_notes": True,
                "move_note": False,
                "days_to_keep_quotations": 15,
            }
        )

        settings.set_values()
        values = settings.get_values()

        self.assertTrue(values["move_internal_notes"])
        self.assertFalse(values["move_note"])
        self.assertEqual(self.IrConfig.get_str("sale_ux.days_to_keep_quotations"), "15")

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

    def _create_price_included_tax_case(self):
        """A 21% tax included in the price, replaced by an exempt tax through a fiscal position."""
        tax = self.env["account.tax"].create(
            {
                "name": "Sale UX 21% included",
                "amount": 21,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "price_include_override": "tax_included",
            }
        )
        exempt = self.env["account.tax"].create(
            {"name": "Sale UX exempt", "amount": 0, "amount_type": "percent", "type_tax_use": "sale"}
        )
        product = self.env["product.product"].create(
            {
                "name": "Sale UX tax included product",
                "type": "consu",
                "list_price": 121.0,
                "taxes_id": [Command.set([tax.id])],
            }
        )
        return tax, exempt, product

    def _price_with_fiscal_position(self, deduct):
        tax, exempt, product = self._create_price_included_tax_case()
        fiscal_position = self.env["account.fiscal.position"].create(
            {"name": "Sale UX FP %s" % deduct, "deduct_price_included_taxes": deduct}
        )
        exempt.write(
            {"original_tax_ids": [Command.set([tax.id])], "fiscal_position_ids": [Command.set([fiscal_position.id])]}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "fiscal_position_id": fiscal_position.id,
                "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1})],
            }
        )
        return order.order_line.price_unit

    def test_fiscal_position_does_not_deduct_price_included_taxes_by_default(self):
        """The price of the line is the final price of the product, not the price without the replaced tax."""
        self.assertEqual(self._price_with_fiscal_position(deduct=False), 121.0)

    def test_fiscal_position_deducts_price_included_taxes_when_setting_is_on(self):
        self.assertEqual(self._price_with_fiscal_position(deduct=True), 100.0)
