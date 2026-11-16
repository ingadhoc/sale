from lxml import etree
from odoo import Command
from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestProductPricelist(SaleUxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pricelist_product = cls.env["product.template"].create(
            {
                "name": "Product with pricelists",
                "list_price": 100.0,
            }
        )
        cls.shown_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Pricelist shown on products",
                "show_products": True,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "compute_price": "fixed",
                            "fixed_price": 42.0,
                        },
                    )
                ],
            }
        )

    def test_read_pricelist_ids_does_not_write(self):
        """Reading pricelist_ids must not write on product.pricelist: price is
        not stored and website_sale's write() clears the whole registry cache."""
        pricelist_model = type(self.env["product.pricelist"])
        origin = pricelist_model.write
        written = []

        def write(records, vals):
            written.append(vals)
            return origin(records, vals)

        self.patch(pricelist_model, "write", write)
        self.pricelist_product.invalidate_recordset(["pricelist_ids"])
        self.assertIn(self.shown_pricelist, self.pricelist_product.pricelist_ids)
        self.assertFalse(written, "Reading pricelist_ids wrote on product.pricelist")

    def test_price_returns_contextual_price(self):
        """price keeps returning the contextual price, on template and variant."""
        self.assertEqual(
            self.shown_pricelist.with_context(pricelist_template_id=self.pricelist_product.id).price,
            42.0,
        )
        variant = self.pricelist_product.product_variant_id
        self.assertEqual(
            self.shown_pricelist.with_context(pricelist_product_id=variant.id).price,
            42.0,
        )

    def test_view_cache_is_not_shared_between_groups(self):
        """The readonly form built for salesmen must not leak to sales managers
        through the view cache, nor the other way around."""
        salesman = self.env["res.users"].create(
            {
                "name": "Sale UX Salesman",
                "login": "sale_ux_salesman",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("sales_team.group_sale_salesman").id,
                        ]
                    )
                ],
            }
        )
        manager = self.env["res.users"].create(
            {
                "name": "Sale UX Sales Manager",
                "login": "sale_ux_sales_manager",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("sales_team.group_sale_manager").id,
                        ]
                    )
                ],
            }
        )
        for first, second in ((salesman, manager), (manager, salesman)):
            with self.subTest(opened_first_by=first.login):
                self.env.registry.clear_cache("templates")
                for user in (first, second):
                    arch = etree.fromstring(
                        self.env["product.pricelist"].with_user(user).get_view(view_type="form")["arch"]
                    )
                    readonly = any(node.get("edit") == "false" for node in arch.xpath("//form"))
                    self.assertEqual(
                        readonly,
                        user == salesman,
                        f"{user.login} got the form of the other group because {first.login} opened it first",
                    )

    def test_template_price_compute_delegates_unknown_base_to_variant(self):
        """Bases that are not template fields (e.g. "partner" from product_customerinfo)
        are resolved on the variant instead of failing with KeyError on the template."""
        variant = self.pricelist_product.product_variant_id
        self.assertTrue(variant)
        product_model = type(self.env["product.product"])
        calls = []

        def _price_compute(records, price_type, *args, **kwargs):
            calls.append(price_type)
            return {rec.id: 77.0 for rec in records}

        self.patch(product_model, "_price_compute", _price_compute)
        prices = self.pricelist_product._price_compute("partner")
        self.assertEqual(prices[self.pricelist_product.id], 77.0)
        self.assertEqual(calls, ["partner"])

    def test_template_price_compute_unknown_base_without_variant_falls_back_to_list_price(self):
        """A template without active variants cannot delegate: it falls back to list_price."""
        self.pricelist_product.product_variant_ids.write({"active": False})
        self.assertFalse(self.pricelist_product.product_variant_id)
        prices = self.pricelist_product._price_compute("partner")
        self.assertEqual(prices[self.pricelist_product.id], 100.0)

    def test_template_price_compute_keeps_standard_bases(self):
        """Bases that are template fields keep the standard behavior."""
        prices = self.pricelist_product._price_compute("list_price")
        self.assertEqual(prices[self.pricelist_product.id], 100.0)
