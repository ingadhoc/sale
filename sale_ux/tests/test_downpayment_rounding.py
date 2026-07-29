##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestDownpaymentRounding(AccountTestInvoicingCommon):
    def test_full_downpayment_half_cent_residual_final_invoice(self):
        """A 100% down payment must leave a zero final invoice, not a 0.01 credit note.

        With round_globally, qty 0.5 at price_unit 1.01 has a raw subtotal of 0.505,
        while the down payment line can only store the rounded 0.51. That -0.005 residual
        used to be amplified into a full cent, flipping the final invoice into a refund.
        """
        # sale_exception (via demo data) trae reglas activas que hacen que action_confirm
        # devuelva un popup sin confirmar la orden (queda en 'draft' y no habria nada que
        # facturar). Las desactivamos para que el escenario sea determinista.
        if "exception.rule" in self.env:
            self.env["exception.rule"].sudo().search([]).write({"active": False})
        self.env.company.tax_calculation_rounding_method = "round_globally"
        # Producto consumible facturado por orden, como el 'product_order_no' que usa el
        # core para sus tests de anticipos: 'consu' + invoice_policy 'order' es lo mas
        # robusto en el stack completo de runbot (un 'service' arrastra service_policy /
        # subscription / timesheet que pueden dejar la factura final sin items facturables).
        # _create_product setea las cuentas de ingreso/gasto; taxes_id vacio para que el
        # subtotal crudo caiga justo en el medio centavo.
        product = self._create_product(name="DP rounding", type="consu", invoice_policy="order", taxes_id=[])
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 0.5, "price_unit": 1.01})],
            }
        )
        order.action_confirm()

        self.env["sale.advance.payment.inv"].with_context(
            active_model="sale.order", active_ids=order.ids, active_id=order.id
        ).create({"advance_payment_method": "percentage", "amount": 100}).create_invoices()
        order.invoice_ids.action_post()

        final_invoice = order._create_invoices(final=True)

        self.assertEqual(final_invoice.move_type, "out_invoice")
        self.assertEqual(final_invoice.amount_total, 0.0)
