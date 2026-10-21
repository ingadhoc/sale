from odoo import Command
from odoo.tests import Form, tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestPriceUnitProductUom(SaleUxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_box_15 = cls.env["uom.uom"].create(
            {
                "name": "Box 15 kg",
                "relative_factor": 15.0,
                "relative_uom_id": cls.uom_kg.id,
            }
        )
        cls.product_kg = cls.env["product.product"].create(
            {
                "name": "Welding wire",
                "type": "consu",
                "list_price": 4.522,
                "uom_id": cls.uom_kg.id,
                "uom_ids": [Command.set([cls.uom_box_15.id])],
                "property_account_income_id": cls.income_account.id,
                "taxes_id": [Command.clear()],
            }
        )

    def _create_line(self, uom, qty=5.0, price_unit=67.83):
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product_kg.id,
                        "product_uom_id": uom.id,
                        "product_uom_qty": qty,
                        "price_unit": price_unit,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )
        return order.order_line

    def test_price_is_shown_in_the_product_unit(self):
        line = self._create_line(self.uom_box_15)

        self.assertAlmostEqual(line.price_unit_product_uom, 4.522)

    def test_price_keeps_four_decimals(self):
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
