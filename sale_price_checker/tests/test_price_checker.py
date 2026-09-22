##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import json

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.tests import tagged
from odoo.tools.misc import format_amount


@tagged("post_install", "-at_install")
class TestPriceChecker(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.tax_included = cls.env["account.tax"].create(
            {
                "name": "Price Checker 21% included",
                "amount_type": "percent",
                "amount": 21.0,
                "type_tax_use": "sale",
                "price_include_override": "tax_included",
                "company_id": cls.company.id,
            }
        )
        cls.tax_excluded = cls.tax_included.copy(
            {
                "name": "Price Checker 21% excluded",
                "price_include_override": "tax_excluded",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Price Checker Product",
                "barcode": "PRICECHECKER01",
                "list_price": 12100.0,
                "sale_ok": True,
                "taxes_id": [(6, 0, cls.tax_included.ids)],
            }
        )

    def _lookup(self, barcode="PRICECHECKER01"):
        response = self.url_open(
            f"/price-checker/{self.company.id}/lookup",
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": {"barcode": barcode}}),
            headers={"Content-Type": "application/json"},
        )
        return response.json()["result"]

    def _formatted(self, amount):
        return format_amount(self.env, amount, self.company.currency_id, lang_code=self.company.partner_id.lang)

    def test_tax_included_in_price(self):
        result = self._lookup()
        self.assertTrue(result["found"])
        self.assertEqual(result["price"], self._formatted(12100.0))
        self.assertEqual(result["price_untaxed"], self._formatted(10000.0))

    def test_tax_excluded_from_price(self):
        self.product.taxes_id = self.tax_excluded
        result = self._lookup()
        self.assertEqual(result["price"], self._formatted(14641.0))
        self.assertEqual(result["price_untaxed"], self._formatted(12100.0))

    def test_without_taxes(self):
        self.product.taxes_id = False
        result = self._lookup()
        self.assertEqual(result["price"], self._formatted(12100.0))
        self.assertFalse(result["price_untaxed"])

    def test_pricelist_with_tax_included(self):
        self.env.ref("base.group_user").sudo().write(
            {"implied_ids": [(4, self.env.ref("product.group_product_pricelist").id)]}
        )
        self.env.registry.clear_cache("groups")
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Price Checker 10% off",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "compute_price": "percentage",
                            "percent_price": 10.0,
                            "applied_on": "3_global",
                        },
                    )
                ],
            }
        )
        self.company.price_checker_pricelist_id = pricelist
        result = self._lookup()
        self.assertEqual(result["price"], self._formatted(10890.0))
        self.assertEqual(result["price_untaxed"], self._formatted(9000.0))
