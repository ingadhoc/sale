##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo import Command
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestInvoiceProductUom(TestSaleCommon):
    """A line sold by packaging is invoiced in the unit of the product."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setting = "sale_product_uom_price.report_in_product_uom"
        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_box_13_6 = cls.env["uom.uom"].create(
            {"name": "Box 13.6 kg", "relative_factor": 13.6, "relative_uom_id": cls.uom_kg.id}
        )
        cls.uom_box_15 = cls.env["uom.uom"].create(
            {"name": "Box 15 kg", "relative_factor": 15.0, "relative_uom_id": cls.uom_kg.id}
        )
        # A packaging whose quantity does not convert into whole hundredths of a kg
        cls.uom_bag_third = cls.env["uom.uom"].create(
            {"name": "Bag 1/3 kg", "relative_factor": 1 / 3, "relative_uom_id": cls.uom_kg.id}
        )
        cls.product_kg = cls.env["product.product"].create(
            {
                "name": "Welding wire",
                "type": "consu",
                "invoice_policy": "order",
                "list_price": 7.27,
                "uom_id": cls.uom_kg.id,
                "uom_ids": [Command.set([cls.uom_box_13_6.id, cls.uom_box_15.id, cls.uom_bag_third.id])],
                "taxes_id": [Command.clear()],
            }
        )

    def _invoice_order(self, uom, qty=5.0, price_unit=98.87):
        order = self._create_order(uom, qty, price_unit)
        order.action_confirm()
        return order, self._invoice_lines(order)

    def _invoice_lines(self, order):
        """A line whose invoicing policy is set by the order type has nothing to invoice until it
        is delivered, so the delivery is stated before invoicing."""
        for line in order.order_line.filtered(lambda line: not line.qty_to_invoice):
            line.qty_delivered = line.product_uom_qty
        return order._create_invoices().invoice_line_ids

    def _create_order(self, uom, qty, price_unit):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product_kg.id,
                            "product_uom_id": uom.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )

    def test_invoice_is_issued_in_the_product_unit(self):
        """5 boxes of 13.6 kg at 98.872 are 68 kg at 7.27."""
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "True")

        _order, invoice_line = self._invoice_order(self.uom_box_13_6)

        self.assertEqual(invoice_line.product_uom_id, self.uom_kg)
        self.assertAlmostEqual(invoice_line.quantity, 68.0)
        self.assertAlmostEqual(invoice_line.price_unit, 7.27)

    def test_the_invoice_adds_up_to_the_order(self):
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "True")

        order, invoice_line = self._invoice_order(self.uom_box_13_6)

        self.assertAlmostEqual(invoice_line.price_subtotal, order.order_line.price_subtotal)

    def test_the_order_counts_the_invoiced_quantity_in_its_own_unit(self):
        """The invoice is in kg, but what the order has to show as invoiced is its 5 boxes."""
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "True")

        order, _invoice_line = self._invoice_order(self.uom_box_13_6)

        self.assertAlmostEqual(order.order_line.qty_invoiced, 5.0)

    def test_a_line_in_the_product_unit_is_not_converted(self):
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "True")

        _order, invoice_line = self._invoice_order(self.uom_kg, qty=68.0, price_unit=7.27)

        self.assertEqual(invoice_line.product_uom_id, self.uom_kg)
        self.assertAlmostEqual(invoice_line.quantity, 68.0)

    def test_without_the_setting_the_invoice_keeps_the_packaging(self):
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "")

        _order, invoice_line = self._invoice_order(self.uom_box_13_6)

        self.assertEqual(invoice_line.product_uom_id, self.uom_box_13_6)
        self.assertAlmostEqual(invoice_line.quantity, 5.0)
        self.assertAlmostEqual(invoice_line.price_unit, 98.87)

    def test_a_report_price_with_taxes_does_not_reach_the_invoice(self):
        """A localization prints the price with VAT, but the invoice line carries the taxes of
        the order line, so the price it takes has to be the one without them."""
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "True")
        line_model = type(self.env["sale.order.line"])
        with patch.object(
            line_model,
            "_get_report_price_unit",
            lambda line, price=None: (line.price_unit if price is None else price) * 1.21,
        ):
            order, invoice_line = self._invoice_order(self.uom_box_15, price_unit=67.83)

        self.assertAlmostEqual(invoice_line.price_subtotal, order.order_line.price_subtotal)

    def test_the_invoice_adds_up_for_a_price_with_extra_decimals(self):
        """A price entered before the setting rounded it: 67.83 per 15 kg box is 4.522 per kg,
        and 75 kg at 4.522 are the 339.15 of the order."""
        order = self._create_order(self.uom_box_15, 5.0, 67.83)
        order.action_confirm()
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "True")

        invoice_line = self._invoice_lines(order)

        self.assertEqual(invoice_line.product_uom_id, self.uom_kg)
        self.assertAlmostEqual(invoice_line.quantity, 75.0)
        self.assertAlmostEqual(invoice_line.price_unit, 4.522)
        self.assertAlmostEqual(invoice_line.price_subtotal, order.order_line.price_subtotal)

    def test_a_quantity_that_does_not_convert_exactly_keeps_the_packaging(self):
        """7 bags of 1/3 kg are 2.3333 kg, which an invoice line states as 2.33: converted, the
        invoice would not add up to the order, so the line is invoiced in its own unit."""
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "True")

        order, invoice_line = self._invoice_order(self.uom_bag_third, qty=7.0, price_unit=10.0)

        self.assertEqual(invoice_line.product_uom_id, self.uom_bag_third)
        self.assertAlmostEqual(invoice_line.quantity, 7.0)
        self.assertAlmostEqual(invoice_line.price_subtotal, order.order_line.price_subtotal)

    def test_a_fraction_of_a_package_is_invoiced_in_the_product_unit(self):
        """Half a box of 13.6 kg is 6.8 kg, which an invoice line states exactly."""
        self.env["ir.config_parameter"].sudo().set_param(self.setting, "True")

        order, invoice_line = self._invoice_order(self.uom_box_13_6, qty=0.5, price_unit=98.872)

        self.assertEqual(invoice_line.product_uom_id, self.uom_kg)
        self.assertAlmostEqual(invoice_line.quantity, 6.8)
        self.assertAlmostEqual(invoice_line.price_subtotal, order.order_line.price_subtotal)
