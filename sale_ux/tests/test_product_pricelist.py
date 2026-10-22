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
