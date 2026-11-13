##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestLostQty(SaleUxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lost_reason_price = cls.env["sale.order.line.lost.reason"].create({"name": "Price"})
        cls.lost_reason_stock = cls.env["sale.order.line.lost.reason"].create({"name": "Out of stock"})

    def _enable_lost_qty(self):
        """The new columns live behind the setting's group, so the form needs it on."""
        self.env.user.group_ids = [Command.link(self.env.ref("sale_ux.group_lost_qty").id)]

    def test_unticking_sold_moves_the_whole_qty(self):
        """Unticking "Sold" leaves the line at 0 with its quantity as unsold."""
        self._enable_lost_qty()
        order = self._create_sale_order()
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                self.assertTrue(line_form.is_sold, "lines are sold by default")
                line_form.is_sold = False
                self.assertEqual(line_form.lost_qty, 2.0)
                self.assertEqual(line_form.product_uom_qty, 0.0)
                line_form.lost_reason_id = self.lost_reason_price

        line = order.order_line
        self.assertEqual(line.product_uom_qty, 0.0)
        self.assertEqual(line.lost_qty, 2.0)
        self.assertEqual(line.lost_reason_id, self.lost_reason_price)

    def test_reticking_sold_gives_the_qty_back(self):
        """Ticking "Sold" again returns the quantity and clears the unsold columns."""
        self._enable_lost_qty()
        order = self._create_sale_order()
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.is_sold = False
                line_form.lost_reason_id = self.lost_reason_price
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.is_sold = True
                self.assertEqual(line_form.product_uom_qty, 2.0)
                self.assertEqual(line_form.lost_qty, 0.0)
                self.assertFalse(line_form.lost_reason_id)

        line = order.order_line
        self.assertEqual(line.product_uom_qty, 2.0)
        self.assertEqual(line.lost_qty, 0.0)
        self.assertFalse(line.lost_reason_id)

    def test_partial_loss_takes_qty_out_of_the_line(self):
        """Loading 5 unsold out of 20 leaves the line at 15."""
        self._enable_lost_qty()
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 20.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.lost_qty = 5.0
                self.assertEqual(line_form.product_uom_qty, 15.0)
                self.assertTrue(line_form.is_sold, "a partially sold line is still sold")
                line_form.lost_reason_id = self.lost_reason_stock

        line = order.order_line
        self.assertEqual(line.product_uom_qty, 15.0)
        self.assertEqual(line.lost_qty, 5.0)

    def test_editing_lost_qty_twice_is_not_cumulative(self):
        """Editing the unsold quantity again before saving recomputes from the quoted total."""
        self._enable_lost_qty()
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 20.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.lost_qty = 5.0
                self.assertEqual(line_form.product_uom_qty, 15.0)
                line_form.lost_qty = 8.0
                self.assertEqual(line_form.product_uom_qty, 12.0)
                line_form.lost_reason_id = self.lost_reason_stock

        self.assertEqual(order.order_line.product_uom_qty, 12.0)
        self.assertEqual(order.order_line.lost_qty, 8.0)

    def test_unticking_sold_by_write_moves_the_whole_qty(self):
        """The editable list and the API write the field with no onchange: the move happens anyway."""
        order = self._create_sale_order()
        order.order_line.write({"is_sold": False, "lost_reason_id": self.lost_reason_price.id})

        line = order.order_line
        self.assertEqual(line.product_uom_qty, 0.0)
        self.assertEqual(line.lost_qty, 2.0)

    def test_reticking_sold_by_write_gives_the_qty_back(self):
        order = self._create_sale_order()
        order.order_line.write({"is_sold": False, "lost_reason_id": self.lost_reason_price.id})
        order.order_line.write({"is_sold": True})

        line = order.order_line
        self.assertEqual(line.product_uom_qty, 2.0)
        self.assertEqual(line.lost_qty, 0.0)
        self.assertFalse(line.lost_reason_id)

    def test_writing_lost_qty_takes_it_out_of_the_line(self):
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 20.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )
        order.order_line.write({"lost_qty": 5.0, "lost_reason_id": self.lost_reason_stock.id})

        line = order.order_line
        self.assertEqual(line.product_uom_qty, 15.0)
        self.assertEqual(line.lost_qty, 5.0)
        self.assertTrue(line.is_sold, "a partially sold line is still sold")

    def test_writing_lost_qty_twice_is_not_cumulative(self):
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 20.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )
        order.order_line.write({"lost_qty": 5.0, "lost_reason_id": self.lost_reason_stock.id})
        order.order_line.write({"lost_qty": 8.0})

        self.assertEqual(order.order_line.product_uom_qty, 12.0)
        self.assertEqual(order.order_line.lost_qty, 8.0)

    def test_lost_qty_without_reason_is_rejected(self):
        """A line cannot be saved with an unsold quantity and no reason."""
        order = self._create_sale_order()
        with self.assertRaises(ValidationError):
            order.order_line.write({"lost_qty": 1.0})

    def test_lost_amount_is_stored(self):
        """The unsold amount is kept, discount included."""
        order = self._create_sale_order()
        order.order_line.write({"lost_qty": 2.0, "lost_reason_id": self.lost_reason_price, "discount": 10.0})
        self.assertEqual(order.order_line.lost_amount, 180.0)

    def test_unsold_lines_are_out_of_report_and_portal(self):
        """Unsold lines feed neither the printed quotation nor the portal."""
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 3.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
            ]
        )
        sold_line, unsold_line = order.order_line
        unsold_line.write(
            {
                "is_sold": False,
                "product_uom_qty": 0.0,
                "lost_qty": 3.0,
                "lost_reason_id": self.lost_reason_price.id,
            }
        )
        lines_to_report = order._get_order_lines_to_report()
        self.assertIn(sold_line, lines_to_report)
        self.assertNotIn(unsold_line, lines_to_report)

    def test_confirming_only_delivers_the_sold_qty(self):
        """The unsold line is left out of what gets invoiced."""
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 3.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
            ]
        )
        sold_line, unsold_line = order.order_line
        unsold_line.write(
            {
                "is_sold": False,
                "product_uom_qty": 0.0,
                "lost_qty": 3.0,
                "lost_reason_id": self.lost_reason_price.id,
            }
        )
        order.action_confirm()
        self.assertEqual(sold_line.qty_to_invoice, 2.0)
        self.assertEqual(unsold_line.qty_to_invoice, 0.0)
        self.assertEqual(order.amount_untaxed, 200.0, "the unsold line adds nothing to the total")

    def test_setting_off_changes_nothing(self):
        """With the setting off a salesman does not see the new columns."""
        self.env["res.config.settings"].create({"group_lost_qty": False}).execute()
        salesman = self.env["res.users"].create(
            {
                "name": "Sale UX Salesman",
                "login": "sale_ux_lost_qty_salesman",
                "group_ids": [Command.link(self.env.ref("sales_team.group_sale_salesman").id)],
            }
        )
        self.assertFalse(salesman.has_group("sale_ux.group_lost_qty"))
        arch = self.env["sale.order"].with_user(salesman).get_view(view_type="form")["arch"]
        self.assertNotIn('name="lost_qty"', arch)
        self.assertNotIn('name="is_sold"', arch)

    def test_setting_on_shows_the_columns(self):
        """With the setting on the columns are in the quotation form."""
        self.env["res.config.settings"].create({"group_lost_qty": True}).execute()
        arch = self.env["sale.order"].get_view(view_type="form")["arch"]
        self.assertIn('name="lost_qty"', arch)
        self.assertIn('name="is_sold"', arch)
