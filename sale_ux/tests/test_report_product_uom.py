##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged

from .common import ProductUomPriceCommon


@tagged("post_install", "-at_install")
class TestReportProductUom(ProductUomPriceCommon):
    def _render_pdf_html(self, order):
        html, _ = self.env["ir.actions.report"]._render_qweb_html("sale.report_saleorder", order.ids)
        return html.decode()

    def test_setting_disabled_keeps_line_unit(self):
        self.IrConfig.set_bool(self.setting, False)
        order = self._create_order(self.uom_box_20, 1.0, 145.40)

        self.assertFalse(order.order_line._get_report_product_uom_values())

    def test_line_in_product_unit_is_not_converted(self):
        self.IrConfig.set_bool(self.setting, True)
        order = self._create_order(self.uom_kg, 20.0, 7.27)

        self.assertFalse(order.order_line._get_report_product_uom_values())

    def test_packaging_line_converted_to_product_unit(self):
        self.IrConfig.set_bool(self.setting, True)
        order = self._create_order(self.uom_box_20, 1.0, 145.40)

        values = order.order_line._get_report_product_uom_values()

        self.assertEqual(values["uom"], self.uom_kg)
        self.assertAlmostEqual(values["qty"], 20.0)
        self.assertAlmostEqual(values["price_unit"], 7.27)
        self.assertAlmostEqual(values["qty"] * values["price_unit"], order.order_line.price_subtotal)

    def test_report_shows_product_unit_and_closes_with_subtotal(self):
        """67.83 per 15 kg box is 4.522 per kg: 75 kg x 4.522 = 339.15, the line subtotal."""
        self.IrConfig.set_bool(self.setting, True)
        order = self._create_order(self.uom_box_15, 5.0, 67.83)

        html = self._render_pdf_html(order)

        self.assertIn("75.00", html)
        self.assertIn("4.522", html)
        self.assertIn("339.15", html)
        self.assertNotIn("67.83", html)

    def test_report_with_discount(self):
        self.IrConfig.set_bool(self.setting, True)
        order = self._create_order(self.uom_box_20, 1.0, 145.40, discount=10.0)
        line = order.order_line
        values = line._get_report_product_uom_values()

        html = self._render_pdf_html(order)

        # Other modules may rework the discount (e.g. final price), so check against the line values
        self.assertAlmostEqual(
            values["qty"] * values["price_unit"] * (1 - line.discount / 100.0), line.price_subtotal, places=2
        )
        self.assertIn("7.27", html)
        self.assertIn(f"{line.price_subtotal:.2f}", html)

    def test_report_without_setting_keeps_packaging_price(self):
        self.IrConfig.set_bool(self.setting, False)
        order = self._create_order(self.uom_box_20, 1.0, 145.40)

        html = self._render_pdf_html(order)

        self.assertIn("145.40", html)

    def test_portal_shows_product_unit_on_both_layouts(self):
        """The online quotation has a table and a small screen block: neither shows the box price."""
        self.IrConfig.set_bool(self.setting, True)
        order = self._create_order(self.uom_box_15, 5.0, 67.83)
        currency = order.currency_id
        price = f"{currency.symbol}\xa04.522" if currency.position == "before" else f"4.522\xa0{currency.symbol}"

        html = str(self.env["ir.qweb"]._render("sale.sale_order_portal_content", {"sale_order": order}))

        self.assertEqual(html.count(price), 2)
        self.assertNotIn("67.83", html)
