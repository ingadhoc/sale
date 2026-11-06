# Copyright 2026 ADHOC SA (http://www.adhoc.com.ar)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import common


class TestSaleProductPackTripleDiscount(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("sale.group_discount_per_so_line")
        cls.pricelist = cls.env["product.pricelist"].create(
            {"name": "Test Pricelist", "discount_policy": "without_discount"}
            if "discount_policy" in cls.env["product.pricelist"]._fields
            else {"name": "Test Pricelist"}
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Partner", "property_product_pricelist": cls.pricelist.id}
        )
        # Own products, not the first two of the base: in a database with several
        # companies those belong to another one and the line fails _check_company.
        cls.component = cls.env["product.product"].create(
            {
                "name": "Test Component",
                "type": "consu",
                "list_price": 100.0,
                "company_id": False,
                "taxes_id": [Command.clear()],
            }
        )
        cls.pack = cls.env["product.product"].create(
            {
                "name": "Test Pack",
                "type": "consu",
                "list_price": 0.0,
                "company_id": False,
                "taxes_id": [Command.clear()],
            }
        )
        cls.pack.product_tmpl_id.write(
            {
                "pack_ok": True,
                "pack_type": "detailed",
                "pack_component_price": "detailed",
                "pack_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.component.id,
                            "quantity": 1.0,
                            "sale_discount": 10.0,
                        }
                    )
                ],
            }
        )

    def _new_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "order_line": [Command.create({"product_id": self.pack.id, "product_uom_qty": 1.0})],
            }
        )

    def _component_line(self, order):
        return order.order_line.filtered("pack_parent_line_id")

    def test_pack_discount_lands_in_discount1(self):
        """The pack sale_discount survives sale_triple_discount, in Discount 1."""
        line = self._component_line(self._new_order())
        self.assertAlmostEqual(line.discount1, 10.0)
        self.assertAlmostEqual(line.discount, 10.0)
        self.assertAlmostEqual(line.price_subtotal, 90.0)

    def test_pack_discount_combines_with_the_other_two(self):
        """Discount 2 and 3 stack on top of the pack discount, they do not replace it."""
        line = self._component_line(self._new_order())
        line.discount2 = 5.0
        self.assertAlmostEqual(line.discount1, 10.0)
        self.assertAlmostEqual(line.discount, 14.5)
        self.assertAlmostEqual(line.price_subtotal, 85.5)

    def test_pack_discount_survives_recompute_prices(self):
        """Recomputing the prices keeps the pack discount in Discount 1."""
        order = self._new_order()
        order._recompute_prices()
        line = self._component_line(order)
        self.assertAlmostEqual(line.discount1, 10.0)
        self.assertAlmostEqual(line.price_subtotal, 90.0)

    def test_totalized_pack_gets_no_discount(self):
        """Only a 'detailed' component price carries the discount to the line."""
        self.pack.product_tmpl_id.pack_component_price = "totalized"
        line = self._component_line(self._new_order())
        self.assertAlmostEqual(line.discount1, 0.0)

    def test_a_line_outside_a_pack_is_untouched(self):
        """A plain line keeps the discount it already had."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "order_line": [Command.create({"product_id": self.component.id, "product_uom_qty": 1.0})],
            }
        )
        self.assertAlmostEqual(order.order_line.discount1, 0.0)
        self.assertAlmostEqual(order.order_line.price_subtotal, 100.0)
