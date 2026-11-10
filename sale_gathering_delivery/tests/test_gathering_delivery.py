from odoo.tests import tagged

from .common import SaleGatheringDeliveryCommon


@tagged("post_install", "-at_install")
class TestSaleGatheringDelivery(SaleGatheringDeliveryCommon):
    def test_delivery_line_is_out_of_the_gathering(self):
        """A delivery line is charged, not gathered.

        Covers `sale.order._get_gathering_lines`: the line keeps its quantity when the
        order is confirmed, and its amount stays out of the gathered total and of the
        balance.
        """
        order = self._create_order(is_gathering=True)
        delivery_line = self._add_delivery_line(order)
        product_line = order.order_line - delivery_line

        with self.subTest("el flete entra al pedido como una línea más"):
            self.assertEqual(order.amount_total, 250.0)

        order.action_confirm()

        with self.subTest("al confirmar, la mercadería se acopia"):
            self.assertEqual(product_line.initial_qty_gathered, 2.0)
            self.assertEqual(product_line.product_uom_qty, 0.0)

        with self.subTest("y el flete no"):
            self.assertEqual(delivery_line.initial_qty_gathered, 0.0)
            self.assertEqual(delivery_line.product_uom_qty, 1.0)
            self.assertEqual(delivery_line.price_subtotal, 50.0)

        with self.subTest("el monto acopiado excluye el flete"):
            self.assertAlmostEqual(order.gathering_amount_with_taxes, 200.0)

        with self.subTest("y el saldo también"):
            self._create_and_pay_gathering_downpayment(order, amount=200.0)
            self.assertAlmostEqual(order.gathering_balance, 200.0)

    def test_fixed_downpayment_invoices_the_delivery_line(self):
        """Covers `sale.advance.payment.inv._create_invoices`.

        The gathering down payment invoice carries the delivery line as well, so the
        customer pays the freight with the gathering. On a non-gathering order the
        override does nothing.
        """
        for is_gathering, expected_total, expected_lines in [(True, 250.0, 2), (False, 200.0, 1)]:
            with self.subTest(acopio=is_gathering):
                order = self._create_order(is_gathering=is_gathering)
                self._add_delivery_line(order)
                order.action_confirm()

                self._create_advance_payment_wizard(order, amount=200.0).create_invoices()
                invoice = order.invoice_ids.filtered(lambda move: move.state != "cancel").sorted("id")[-1]

                self.assertEqual(len(invoice.invoice_line_ids), expected_lines)
                self.assertAlmostEqual(invoice.amount_total, expected_total)
                self.assertEqual(
                    bool(invoice.invoice_line_ids.sale_line_ids.filtered("is_delivery")),
                    is_gathering,
                )

    def test_downpayment_with_delivery_counts_as_downpayment(self):
        """Covers `account.move._is_downpayment`.

        A gathering invoice whose only non-down-payment line is the freight is still a
        down payment invoice. Without a gathering order the core answer is kept.
        """
        gathering = self._create_order(is_gathering=True)
        self._add_delivery_line(gathering)
        gathering.action_confirm()
        self._create_advance_payment_wizard(gathering, amount=200.0).create_invoices()
        gathering_invoice = gathering.invoice_ids.filtered(lambda move: move.state != "cancel").sorted("id")[-1]

        with self.subTest("anticipo de acopio con flete"):
            self.assertTrue(gathering_invoice.invoice_line_ids.filtered("is_downpayment"))
            self.assertTrue(gathering_invoice.invoice_line_ids.filtered(lambda line: not line.is_downpayment))
            self.assertTrue(gathering_invoice._is_downpayment())

        regular = self._create_order(is_gathering=False)
        regular.action_confirm()
        regular._create_invoices()
        regular_invoice = regular.invoice_ids.sorted("id")[-1]

        with self.subTest("factura común sin acopio"):
            self.assertFalse(regular_invoice._is_downpayment())
