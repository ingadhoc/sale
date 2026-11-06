from odoo.tests import tagged

from .common import SaleGatheringCommon


@tagged("post_install", "-at_install")
class TestSaleGatheringSplit(SaleGatheringCommon):
    """Cover the `sale_gathering.split_invoice_and_credit_note` branch.

    With the parameter on, invoicing a withdrawal splits the move in two —an
    invoice for the products and a credit note for the down payment— that are
    linked by `reversed_entry_id` and reconciled against each other when they
    are posted.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_bool("sale_gathering.split_invoice_and_credit_note", True)

    def _withdraw_and_invoice(self, *, withdrawn=1.0):
        order = self._confirm_gathering_order()
        self._create_and_pay_gathering_downpayment(order, amount=250.0)

        gathering_line = order.order_line.filtered(lambda line: not line.is_downpayment)
        gathering_line.write({"product_uom_qty": withdrawn})

        invoices_before = order.invoice_ids
        self._create_invoice_gathering_zero_wizard(order).create_invoices()
        return order, order.invoice_ids - invoices_before

    def test_split_creates_an_invoice_and_a_credit_note_as_canje(self):
        order, invoices = self._withdraw_and_invoice()

        self.assertEqual(len(invoices), 2, "El canje tiene que salir en dos comprobantes")
        invoice = invoices.filtered(lambda move: move.move_type == "out_invoice")
        credit_note = invoices.filtered(lambda move: move.move_type == "out_refund")
        self.assertEqual(len(invoice), 1)
        self.assertEqual(len(credit_note), 1)

        # la factura lleva el producto retirado y la nota de credito el anticipo
        self.assertTrue(invoice.invoice_line_ids.filtered(lambda line: line.display_type == "product"))
        self.assertFalse(invoice.invoice_line_ids.filtered("is_downpayment"))
        self.assertTrue(credit_note.invoice_line_ids.filtered("is_downpayment"))

        self.assertAlmostEqual(invoice.amount_total, 100.0)
        self.assertAlmostEqual(credit_note.amount_total, 100.0)
        self.assertEqual(invoice.ref, "Canje")
        self.assertEqual(credit_note.ref, "Canje")
        self.assertEqual(credit_note.reversed_entry_id, invoice)

    def test_posting_the_split_reconciles_the_credit_note_with_the_invoice(self):
        order, invoices = self._withdraw_and_invoice()

        # el anticipo ya esta cobrado, asi que el canje no deja saldo: el balance no cambia
        balance_before = order.gathering_balance

        invoices.action_post()

        self.assertEqual(set(invoices.mapped("state")), {"posted"})
        receivable_lines = invoices.line_ids.filtered(lambda line: line.account_id.account_type == "asset_receivable")
        self.assertTrue(receivable_lines, "El canje tiene que mover la cuenta a cobrar")
        self.assertTrue(
            all(receivable_lines.mapped("reconciled")),
            "La factura y su nota de credito tienen que quedar conciliadas entre si",
        )
        self.assertEqual(len(receivable_lines.mapped("full_reconcile_id")), 1)

        order.invalidate_recordset(["gathering_balance"])
        self.assertAlmostEqual(order.gathering_balance, balance_before)

    def test_without_the_parameter_the_canje_is_a_single_invoice(self):
        self.env["ir.config_parameter"].sudo().set_bool("sale_gathering.split_invoice_and_credit_note", False)

        _order, invoices = self._withdraw_and_invoice()

        self.assertEqual(len(invoices), 1, "Sin el parametro el canje sale en un solo comprobante")
        self.assertTrue(invoices.invoice_line_ids.filtered("is_downpayment"))
        self.assertTrue(invoices.invoice_line_ids.filtered(lambda line: line.display_type == "product"))
        self.assertAlmostEqual(invoices.amount_total, 0.0)
