from odoo.tests import tagged

from .common import SaleGatheringCommon


@tagged("post_install", "-at_install")
class TestSaleGatheringOrder(SaleGatheringCommon):
    def test_action_confirm_moves_quantities_to_initial_qty(self):
        order = self._create_order()

        order.action_confirm()

        self.assertEqual(order.state, "sale")
        self.assertTrue(order.is_gathering)
        self.assertEqual(order.order_line.product_uom_qty, 0.0)
        self.assertEqual(order.order_line.initial_qty_gathered, 2.0)

    def test_gathering_flow_computes_balances_after_paid_downpayment_and_withdrawal(self):
        order = self._confirm_gathering_order()
        self._create_and_pay_gathering_downpayment(order, amount=250.0)

        gathering_line = order.order_line.filtered(lambda line: not line.is_downpayment)
        gathering_line.write({"product_uom_qty": 1.0})

        order._compute_has_gathering_invoice()
        order._compute_gathering_balance()
        order._compute_withdrawn_amount()

        self.assertTrue(order.has_gathering_invoice)
        self.assertAlmostEqual(order.gathering_amount_with_taxes, 200.0)
        self.assertAlmostEqual(order.gathering_balance, 150.0)
        self.assertAlmostEqual(order.withdrawn_amount, 50.0)

    def test_cancelled_downpayment_excluded_from_gathering_balance(self):
        order = self._confirm_gathering_order()
        self._create_and_pay_gathering_downpayment(order, amount=250.0)

        gathering_line = order.order_line.filtered(lambda line: not line.is_downpayment)
        gathering_line.write({"product_uom_qty": 1.0})

        wizard = self._create_advance_payment_wizard(order, amount=500.0)
        wizard.create_invoices()
        second_downpayment_line = order.order_line.filtered(
            lambda line: line.is_downpayment and not line.display_type
        ).sorted("id")[-1]
        cancelled_invoice = second_downpayment_line.invoice_lines.move_id
        self.assertTrue(cancelled_invoice)
        cancelled_invoice.button_cancel()
        self.assertEqual(second_downpayment_line._get_downpayment_state(), "cancel")

        order._compute_gathering_balance()
        order._compute_withdrawn_amount()

        self.assertAlmostEqual(order.gathering_balance, 150.0)
        self.assertAlmostEqual(order.withdrawn_amount, 50.0)

    def test_invoice_gathering_zero_creates_exchange_invoice_lines(self):
        order = self._confirm_gathering_order()
        self._create_and_pay_gathering_downpayment(order, amount=250.0)

        gathering_line = order.order_line.filtered(lambda line: not line.is_downpayment)
        gathering_line.write({"product_uom_qty": 1.0})

        wizard = self._create_invoice_gathering_zero_wizard(order)
        wizard.create_invoices()

        posted_or_draft_invoices = order.invoice_ids.filtered(lambda move: move.state != "cancel")
        canje_invoice = posted_or_draft_invoices.sorted("id")[-1]
        self.assertTrue(canje_invoice.invoice_line_ids.filtered(lambda line: line.display_type == "product"))
        self.assertTrue(canje_invoice.invoice_line_ids.filtered("is_downpayment"))
