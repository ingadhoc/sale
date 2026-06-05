from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import SaleGatheringCommon


@tagged("post_install", "-at_install")
class TestSaleGatheringWizards(SaleGatheringCommon):
    def test_invoice_gathering_zero_method_requires_gathering_order(self):
        order = self._create_order(is_gathering=False)

        with self.assertRaises(ValidationError):
            self.env["sale.advance.payment.inv"].with_context(active_ids=order.ids).create(
                {
                    "advance_payment_method": "invoice_gathering_zero",
                }
            )

    def test_first_gathering_advance_invoice_sets_acopio_reference(self):
        order = self._confirm_gathering_order()

        wizard = self._create_advance_payment_wizard(order, amount=150.0)
        wizard.create_invoices()

        invoice = order.invoice_ids.filtered(lambda move: move.state != "cancel").sorted("id")[-1]
        self.assertEqual(invoice.ref, "Acopio")
        self.assertTrue(invoice.invoice_line_ids.filtered("is_downpayment"))
