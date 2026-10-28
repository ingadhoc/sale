##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.base_exception.exceptions import BaseExceptionError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSaleExceptionPriceSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rule = cls.env.ref("sale_exception_price_security.discount_restriction")
        # Only this module's rule decides, no matter what the database carries
        cls.env["exception.rule"].search([("id", "!=", cls.rule.id)]).write({"active": False})
        # A pricelist with no discount item: price_security then reads the whole
        # line discount as the manual one, so what the restriction allows is
        # exactly the 0-10% below, with no pricelist share to subtract.
        cls.pricelist = cls.env["product.pricelist"].create({"name": "Discount Restriction Pricelist"})
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Discount Restriction Customer",
                "property_product_pricelist": cls.pricelist.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Restricted Product", "type": "consu", "list_price": 100.0}
        )
        cls.free_product = cls.env["product.product"].create(
            {
                "name": "Free Price Product",
                "type": "consu",
                "list_price": 100.0,
                "can_modify_prices": True,
            }
        )
        groups = "sales_team.group_sale_salesman,sale.group_discount_per_so_line"
        cls.seller = new_test_user(
            cls.env,
            login="seps_restricted_seller",
            groups=f"{groups},price_security.group_only_view",
        )
        cls.free_seller = new_test_user(cls.env, login="seps_free_seller", groups=groups)
        cls.env["res.users.discount_restriction"].create(
            {
                "user_id": cls.seller.id,
                "pricelist_id": cls.pricelist.id,
                "min_discount": 0.0,
                "max_discount": 10.0,
            }
        )

    def _new_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "user_id": self.seller.id,
            }
        )

    def _new_line(self, order, product=None, **extra_vals):
        vals = {
            "order_id": order.id,
            "product_id": (product or self.product).id,
            "product_uom_qty": 1,
            **extra_vals,
        }
        return self.env["sale.order.line"].with_user(self.seller).create(vals)

    def _set_discount(self, line, discount):
        """Set the manual discount through the channel the installed discount stack
        leaves open: with sale_triple_discount `discount` becomes readonly and
        discount3 is the manual one."""
        field = "discount3" if "discount3" in line._fields else "discount"
        line.with_user(self.seller).write({field: discount})

    def test_discount_restriction_defers_to_the_sale_exception(self):
        """The discount check stops being an immediate error and becomes a sale
        exception: the line can be edited, and the order is the one that is stopped.

        Since 20.0 base_exception raises BaseExceptionError instead of returning the
        exceptions, so what the test checks is whether the action is stopped.
        """
        order = self._new_order()
        line = self._new_line(order)

        with self.subTest("un descuento fuera de rango no corta la edición de la línea"):
            # Without this module price_security raises UserError here
            self._set_discount(line, 25.0)
            self.assertAlmostEqual(line.discount, 25.0, places=2)

        with self.subTest("al confirmar, la regla del módulo frena el pedido"):
            self.assertFalse(line.with_user(self.seller).check_discount_ok())
            with self.assertRaises(BaseExceptionError):
                order.with_user(self.seller).action_confirm()
            self.assertEqual(order.state, "draft")
            # What exception_ids ends up holding cannot be asserted from a test:
            # detect_exceptions() stores it inside `with registry.cursor()`, which
            # under a TestCursor is a savepoint rolled back on close
            # (odoo/tests/test_cursor.py:35). The raise is what stops the order.

        with self.subTest("la misma regla también frena imprimir"):
            with self.assertRaises(BaseExceptionError):
                order.with_user(self.seller).detect_print_exceptions()

        with self.subTest("ignorando la excepción, el mismo pedido se confirma"):
            order.ignore_exception = True
            order.with_user(self.seller).action_confirm()
            self.assertEqual(order.state, "sale")

        with self.subTest("un descuento dentro del rango confirma sin excepción"):
            allowed = self._new_order()
            allowed_line = self._new_line(allowed)
            self._set_discount(allowed_line, 10.0)
            self.assertTrue(allowed_line.with_user(self.seller).check_discount_ok())
            allowed.with_user(self.seller).action_confirm()
            self.assertEqual(allowed.state, "sale")

    def test_check_discount_ok_lets_the_line_pass(self):
        """The three conditions that take a line out of the discount check."""
        order = self._new_order()

        restricted = self._new_line(order)
        self._set_discount(restricted, 25.0)
        with self.subTest("control: la línea restringida sí falla el chequeo"):
            self.assertFalse(restricted.with_user(self.seller).check_discount_ok())

        free = self._new_line(order, product=self.free_product)
        self._set_discount(free, 25.0)
        with self.subTest("un producto que permite modificar precios no se controla"):
            self.assertTrue(free.with_user(self.seller).check_discount_ok())

        with self.subTest("un usuario sin el grupo de solo ver precios no se controla"):
            self.assertTrue(restricted.with_user(self.free_seller).check_discount_ok())

        section = self.env["sale.order.line"].create(
            {"order_id": order.id, "name": "Sección", "display_type": "line_section"}
        )
        with self.subTest("una línea de sección no se controla"):
            self.assertTrue(section.with_user(self.seller).check_discount_ok())
