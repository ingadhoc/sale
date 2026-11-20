##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import Form, tagged

from .common import ProductUomPriceCommon


@tagged("post_install", "-at_install")
class TestPriceUnitProductUom(ProductUomPriceCommon):
    """Without the setting, the unit price of the line rules and the column follows it."""

    def setUp(self):
        super().setUp()
        self.IrConfig.set_param(self.setting, "")

    def _create_line(self, uom, qty=5.0, price_unit=67.83):
        return self._create_order(uom, qty, price_unit).order_line

    def test_price_is_shown_in_the_product_unit(self):
        line = self._create_line(self.uom_box_15)

        self.assertAlmostEqual(line.price_unit_product_uom, 4.522)

    def test_price_keeps_four_decimals(self):
        # Without the setting the line is not priced per product unit, so the conversion is the
        # only source of the price and its decimals are what makes the subtotal match
        """2 decimals would round 4.5223 to 4.52 and the subtotal would not match."""
        line = self._create_line(self.uom_box_15, price_unit=67.835)

        self.assertAlmostEqual(line.price_unit_product_uom, 4.5223)

    def test_a_line_at_zero_can_still_be_priced_per_product_unit(self):
        """Zero is a valid price: what tells the column apart is the UoM, not the value."""
        line = self._create_line(self.uom_box_15, price_unit=0.0)

        self.assertFalse(line.price_unit_product_uom)
        self.assertTrue(line.price_unit_product_uom_editable)

        with Form(line.order_id) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit_product_uom = 5.0

        self.assertAlmostEqual(line.price_unit, 75.0)

    def test_line_in_the_product_unit_is_not_editable(self):
        line = self._create_line(self.uom_kg, qty=75.0, price_unit=4.522)

        self.assertFalse(line.price_unit_product_uom_editable)

    def test_line_in_the_product_unit_has_no_price(self):
        line = self._create_line(self.uom_kg, qty=75.0, price_unit=4.522)

        self.assertFalse(line.price_unit_product_uom)

    def test_editing_the_price_updates_the_line_unit_price(self):
        line = self._create_line(self.uom_box_15)

        with Form(line.order_id) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit_product_uom = 5.0

        self.assertAlmostEqual(line.price_unit, 75.0)
        self.assertAlmostEqual(line.price_subtotal, 375.0)

    def test_editing_the_line_unit_price_updates_the_price(self):
        line = self._create_line(self.uom_box_15)

        line.price_unit = 60.0

        self.assertAlmostEqual(line.price_unit_product_uom, 4.0)

    def test_price_rounding_follows_the_line_unit_price(self):
        """4.5222 per kg is 67.83 per box, which is 4.522 per kg again."""
        line = self._create_line(self.uom_box_15)

        with Form(line.order_id) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit_product_uom = 4.5222

        self.assertAlmostEqual(line.price_unit, 67.83)
        self.assertAlmostEqual(line.price_unit_product_uom, 4.522)

    def test_manual_price_survives_a_quantity_change(self):
        line = self._create_line(self.uom_box_15)

        with Form(line.order_id) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit_product_uom = 5.0
                line_form.product_uom_qty = 8.0

        self.assertAlmostEqual(line.price_unit, 75.0)

    def test_section_line_has_no_price(self):
        line = self._create_line(self.uom_box_15)
        section = self.env["sale.order.line"].create(
            {"order_id": line.order_id.id, "name": "A section", "display_type": "line_section"}
        )

        self.assertFalse(section.price_unit_product_uom)


@tagged("post_install", "-at_install")
class TestPriceUnitPerProductUom(ProductUomPriceCommon):
    """With the setting, the price per product unit rules and the unit price follows it."""

    def setUp(self):
        super().setUp()
        self.IrConfig.set_param(self.setting, "True")

    def test_the_price_of_the_pricelist_is_rounded_per_product_unit(self):
        """7.27 per kg is 98.872 per 13.6 kg box, which the rule rounds to 98.87: that is
        7.2699 per kg, and the price of the line follows the 7.27 that is printed."""
        self._add_pricelist_rule(price_round=0.01)

        line = self._create_order(self.uom_box_13_6, 5.0).order_line

        self.assertAlmostEqual(line.price_unit_product_uom, 7.27)
        self.assertAlmostEqual(line.price_unit, 98.872)

    def test_the_printed_price_closes_with_the_subtotal(self):
        self._add_pricelist_rule(price_round=0.01)

        line = self._create_order(self.uom_box_13_6, 5.0).order_line
        values = line._get_report_product_uom_values()

        self.assertAlmostEqual(values["qty"] * values["price_unit"], line.price_subtotal)

    def test_the_price_stays_one_of_the_pricelist(self):
        """The rounding is ours, so the line is not left looking like a manually priced one and
        the pricelist goes on pricing it."""
        self._add_pricelist_rule(price_round=0.01)
        line = self._create_order(self.uom_box_13_6, 5.0).order_line

        line.product_uom_qty = 8.0

        self.assertAlmostEqual(line.price_unit, 98.872)
        self.assertAlmostEqual(line.technical_price_unit, 98.872)

    def test_a_price_written_over_the_api_is_rounded_too(self):
        """4.522 per kg is printed as 4.52, so 67.83 per box is not a price the line can keep."""
        line = self._create_order(self.uom_box_15, 5.0, 67.83).order_line

        self.assertAlmostEqual(line.price_unit_product_uom, 4.52)
        self.assertAlmostEqual(line.price_unit, 67.80)

    def test_a_price_typed_by_hand_is_rounded_too(self):
        line = self._create_order(self.uom_box_15, 5.0, 67.83).order_line

        with Form(line.order_id) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit = 68.50

        self.assertAlmostEqual(line.price_unit_product_uom, 4.57)
        self.assertAlmostEqual(line.price_unit, 68.55)

    def test_editing_the_price_per_product_unit_still_works(self):
        line = self._create_order(self.uom_box_15, 5.0, 67.83).order_line

        with Form(line.order_id) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit_product_uom = 5.0

        self.assertAlmostEqual(line.price_unit, 75.0)
        self.assertAlmostEqual(line.price_subtotal, 375.0)

    def test_a_line_in_the_product_unit_is_left_alone(self):
        """Nothing to round: the price is already the one of the product unit."""
        line = self._create_order(self.uom_kg, 75.0, 4.5223).order_line

        self.assertAlmostEqual(line.price_unit, 4.5223)
