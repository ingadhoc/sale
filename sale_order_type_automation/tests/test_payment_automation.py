##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPaymentAutomation(AccountTestInvoicingCommon):
    @classmethod
    def setup_independent_user(cls):
        # Keep superuser context for setup in deployments with stricter product ACLs.
        return None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_journal = cls.company_data["default_journal_bank"]
        cls.sale_type = cls.env["sale.order.type"].create(
            {
                "name": "Test Payment Automation",
                "company_id": cls.env.company.id,
                "payment_atomation": "validate_payment",
                "payment_journal_id": cls.payment_journal.id,
            }
        )

    @classmethod
    def _create_move(cls, move_type, **kwargs):
        return cls._create_invoice_one_line(move_type=move_type, price_unit=100.0, tax_ids=[], **kwargs)

    def test_prepare_payment_vals_follow_document_direction(self):
        """El sentido del pago se deriva del tipo de documento, no del partner_type:
        una NC de cliente devuelve plata y una NC de proveedor la recibe."""
        expected = {
            "out_invoice": ("customer", "inbound"),
            "out_refund": ("customer", "outbound"),
            "in_invoice": ("supplier", "outbound"),
            "in_refund": ("supplier", "inbound"),
        }
        for move_type, (partner_type, payment_type) in expected.items():
            with self.subTest(move_type=move_type):
                move = self._create_move(move_type)
                vals = self.env["account.move"]._prepare_dict_account_payment(move, self.payment_journal)
                self.assertEqual(vals["partner_type"], partner_type)
                self.assertEqual(vals["payment_type"], payment_type)

    def test_customer_invoice_registers_inbound_payment(self):
        invoice = self._create_move("out_invoice", sale_type_id=self.sale_type)

        invoice.action_post()

        payment = invoice.reconciled_payment_ids
        self.assertEqual(len(payment), 1, "La automatización debe crear un único pago")
        self.assertEqual(payment.partner_type, "customer")
        self.assertEqual(payment.payment_type, "inbound", "Cobrar una factura de cliente entra plata")
        self.assertEqual(invoice.amount_residual, 0.0, "El pago debe quedar conciliado con la factura")
        self.assertEqual(invoice.matched_payment_ids, payment, "El pago debe quedar linkeado a la factura")

    def test_customer_refund_registers_outbound_payment(self):
        """Ticket 124193: la NC de cliente registraba un recibo de dinero (inbound)
        en lugar de una devolución (outbound), dejando el asiento contable invertido."""
        refund = self._create_move("out_refund", sale_type_id=self.sale_type)

        refund.action_post()

        payment = refund.reconciled_payment_ids
        self.assertEqual(len(payment), 1, "La automatización debe crear un único pago")
        self.assertEqual(payment.partner_type, "customer")
        self.assertEqual(payment.payment_type, "outbound", "Devolver una NC de cliente saca plata")
        self.assertEqual(refund.amount_residual, 0.0, "El pago debe quedar conciliado con la NC")
        self.assertEqual(refund.matched_payment_ids, payment, "El pago debe quedar linkeado a la NC")
        receivable_line = payment.move_id.line_ids.filtered(lambda x: x.account_type == "asset_receivable")
        self.assertGreater(
            receivable_line.debit,
            0.0,
            "La devolución debe debitar la cuenta a cobrar, revirtiendo el cobro original",
        )

    def test_payment_journal_requires_manual_method_on_both_directions(self):
        """Sin método manual outbound el journal no sirve para pagar una NC, así que
        no debe poder configurarse en el tipo de orden de venta."""
        journal = self.env["account.journal"].create(
            {
                "name": "Bank Without Outbound Manual",
                "type": "bank",
                "code": "BNKNO",
                "company_id": self.env.company.id,
            }
        )
        journal.outbound_payment_method_line_ids.unlink()

        self.assertNotIn(journal, self.env["account.journal"].search(self.sale_type.payment_journal_domain))
        with self.assertRaises(ValidationError):
            self.sale_type.payment_journal_id = journal
