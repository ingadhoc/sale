# Copyright 2025 ADHOC SA (http://www.adhoc.com.ar)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import common


class TestSaleTripleDiscountLock(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("sale.group_discount_per_so_line")
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        products = cls.env["product.product"].search([], limit=2)
        cls.product1 = products[0]
        cls.product2 = products[1]
        cls.product1.write(
            {
                "name": "Test Product 1",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 600.0,
            }
        )
        cls.product2.write(
            {
                "name": "Test Product 2",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 60.0,
            }
        )
        cls.tax = cls.env["account.tax"].create(
            {
                "name": "TAX 15%",
                "amount_type": "percent",
                "type_tax_use": "sale",
                "amount": 15.0,
            }
        )
        order_vals = {"partner_id": cls.partner.id}
        if "ignore_exception" in cls.env["sale.order"]._fields:
            order_vals["ignore_exception"] = True
        cls.order = cls.env["sale.order"].create(order_vals)
        so_line = cls.env["sale.order.line"]
        line1_vals = {
            "order_id": cls.order.id,
            "product_id": cls.product1.id,
            "name": "Line 1",
            "product_uom_qty": 1.0,
            "tax_ids": [(6, 0, [cls.tax.id])],
            "price_unit": 600.0,
        }
        line2_vals = {
            "order_id": cls.order.id,
            "product_id": cls.product2.id,
            "name": "Line 2",
            "product_uom_qty": 10.0,
            "tax_ids": [(6, 0, [cls.tax.id])],
            "price_unit": 60.0,
        }
        if "ignore_exception" in so_line._fields:
            line1_vals["ignore_exception"] = True
            line2_vals["ignore_exception"] = True
        cls.so_line1 = so_line.create(line1_vals)
        cls.so_line2 = so_line.create(line2_vals)

    def test_01_discount2_preserved_on_qty_change(self):
        self.so_line1.discount2 = 12.0
        self.so_line1.discount3 = 5.0
        self.so_line1.product_uom_qty = 5
        self.assertAlmostEqual(self.so_line1.discount2, 12.0)
        self.assertAlmostEqual(self.so_line1.discount3, 5.0)

    def test_02_discount2_preserved_on_update_prices(self):
        self.so_line1.discount2 = 15.0
        self.so_line1.discount3 = 8.0
        self.so_line2.discount2 = 20.0
        self.so_line2.discount3 = 3.0
        self.order.action_update_prices()
        self.assertAlmostEqual(self.so_line1.discount2, 15.0)
        self.assertAlmostEqual(self.so_line1.discount3, 8.0)
        self.assertAlmostEqual(self.so_line2.discount2, 20.0)
        self.assertAlmostEqual(self.so_line2.discount3, 3.0)

    def test_03_pricelist_discount_goes_to_discount1(self):
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Test Pricelist 10%",
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "percentage",
                            "percent_price": 10,
                        }
                    )
                ],
            }
        )
        self.so_line1.discount2 = 12.0
        self.so_line1.discount3 = 5.0
        self.order.pricelist_id = pricelist
        self.order.action_update_prices()
        self.assertAlmostEqual(self.so_line1.discount1, 10.0)
        self.assertAlmostEqual(self.so_line1.discount2, 12.0)
        self.assertAlmostEqual(self.so_line1.discount3, 5.0)

    def test_04_total_discount_computed_correctly(self):
        self.so_line1.discount1 = 10.0
        self.so_line1.discount2 = 20.0
        self.so_line1.discount3 = 30.0
        expected = 100 - (1 - 0.10) * (1 - 0.20) * (1 - 0.30) * 100
        self.assertAlmostEqual(self.so_line1.discount, expected)

    def test_05_pricelist_with_qty_rule_preserves_discount2(self):
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Pricelist Qty >= 50",
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "percentage",
                            "percent_price": 20,
                            "min_quantity": 50,
                        }
                    )
                ],
            }
        )
        self.order.pricelist_id = pricelist
        self.order.action_update_prices()
        self.assertAlmostEqual(self.so_line1.discount1, 0.0)
        self.so_line1.discount2 = 15.0
        self.so_line1.discount3 = 10.0
        self.so_line1.product_uom_qty = 51
        self.assertAlmostEqual(self.so_line1.discount1, 20.0)
        self.assertAlmostEqual(self.so_line1.discount2, 15.0)
        self.assertAlmostEqual(self.so_line1.discount3, 10.0)

    def test_06_invoicing_preserves_triple_discounts(self):
        self.so_line1.discount1 = 10.0
        self.so_line1.discount2 = 15.0
        self.so_line1.discount3 = 5.0
        self.order.action_confirm()
        if self.order.state == "waiting_approval":
            self.order.action_approve()
            self.order.action_confirm()
        for line in self.order.order_line:
            if not line.qty_to_invoice and line.product_id.invoice_policy == "delivery":
                line.qty_delivered = line.product_uom_qty
        self.order._create_invoices()
        invoice = self.order.invoice_ids[0]
        inv_line = invoice.invoice_line_ids.filtered(lambda i: i.product_id == self.product1)
        self.assertTrue(inv_line)
        self.assertAlmostEqual(inv_line.discount1, 10.0)
        self.assertAlmostEqual(inv_line.discount2, 15.0)
        self.assertAlmostEqual(inv_line.discount3, 5.0)
        self.assertAlmostEqual(inv_line.discount, self.so_line1.discount, places=2)
