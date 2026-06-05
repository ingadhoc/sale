from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestAccountMove(SaleUxCommon):
    def test_compute_narration_keeps_sale_invoice_note_when_propagating(self):
        self.IrConfig.set_param("sale.propagate_note", "True")
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_origin": "S00001",
                "narration": "Terms from sale order",
            }
        )

        invoice._compute_narration()

        self.assertIn("Terms from sale order", str(invoice.narration))

    def test_compute_narration_recomputes_when_note_is_not_propagated(self):
        self.IrConfig.set_param("sale.propagate_note", "False")
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_origin": "S00002",
                "narration": "Will be recomputed",
            }
        )

        invoice._compute_narration()

        self.assertNotEqual(invoice.narration, "Will be recomputed")
