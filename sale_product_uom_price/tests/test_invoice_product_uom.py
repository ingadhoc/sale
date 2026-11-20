##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
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
        cls.product_kg = cls.env["product.product"].create(
            {
                "name": "Welding wire",
                "type": "consu",
                "invoice_policy": "order",
                "list_price": 7.27,
                "uom_id": cls.uom_kg.id,
                "uom_ids": [Command.set([cls.uom_box_13_6.id])],
                "taxes_id": [Command.clear()],
            }
        )

    def _invoice_order(self, uom, qty=5.0, price_unit=98.87):
        order = self.env["sale.order"].create(
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
        order.action_confirm()
        return order, order._create_invoices().invoice_line_ids

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
