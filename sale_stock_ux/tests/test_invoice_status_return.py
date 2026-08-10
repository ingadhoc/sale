from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestInvoiceStatusReturn(AccountTestInvoicingCommon):
    """Estado de facturación de la OV tras devoluciones (ticket 123997).

    En ``sale_stock_ux`` una devolución PARCIAL totalmente facturada debe
    quedar "invoiced" (lo entregado neto se facturó), pero una devolución
    TOTAL debe caer a "no" (no queda nada por facturar), igual que el core de
    Odoo. Antes del fix la devolución total quedaba erróneamente "invoiced".
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        # Entrega en 1 paso para un escenario determinista.
        cls.warehouse.delivery_steps = "ship_only"
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner", "customer_rank": 1})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test almacenable",
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "order",
                "list_price": 100.0,
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
                "property_account_expense_id": cls.company_data["default_account_expense"].id,
            }
        )
        # Evitar que reglas de excepción bloqueen la confirmación en runbot.
        # sudo() porque el usuario de AccountTestInvoicingCommon no está en el
        # grupo "Exception manager" y sin él el write falla con AccessError.
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].sudo().search([("active", "=", True)]).write({"active": False})

    def _create_order(self, qty):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": qty, "price_unit": 100.0})],
            }
        )
        order.action_confirm()
        return order

    def _validate(self, picking):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.move_line_ids.unlink()
            move.quantity = move.product_uom_qty
            move.picked = True
        picking._action_done()

    def _make_return(self, picking, quantity):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_ids=picking.ids, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.to_refund = True
            line.quantity = quantity
        action = wizard.action_create_returns()
        returned = self.env["stock.picking"].browse(action["res_id"])
        self._validate(returned)
        return returned

    def _invoice(self, order):
        invoices = order._create_invoices(final=True)
        invoices.action_post()
        return invoices

    def test_total_return_is_nothing_to_invoice(self):
        """Devolución total: tras la nota de crédito el estado es "no"."""
        order = self._create_order(1.0)
        line = order.order_line
        delivery = order.picking_ids
        self._validate(delivery)
        self._invoice(order)
        self.assertEqual(line.invoice_status, "invoiced", "Entregado y facturado debe ser 'invoiced'")

        # Devolvemos TODO -> queda pendiente la nota de crédito.
        self._make_return(delivery, quantity=1.0)
        self.assertEqual(line.invoice_status, "to invoice", "Con la NC pendiente debe ser 'to invoice'")

        # Emitimos la nota de crédito -> no queda nada por facturar.
        self._invoice(order)
        self.assertEqual(line.invoice_status, "no", "Devolución total facturada debe quedar 'no' (nada que facturar)")

    def test_partial_return_stays_invoiced(self):
        """Devolución parcial: tras la nota de crédito sigue "invoiced"."""
        order = self._create_order(2.0)
        line = order.order_line
        delivery = order.picking_ids
        self._validate(delivery)
        self._invoice(order)
        self.assertEqual(line.invoice_status, "invoiced")

        self._make_return(delivery, quantity=1.0)
        self.assertEqual(line.invoice_status, "to invoice")

        self._invoice(order)
        self.assertEqual(line.invoice_status, "invoiced", "Devolución parcial facturada neta debe quedar 'invoiced'")

    def test_no_return_full_invoice_stays_invoiced(self):
        """Sin devolución: entregado y facturado queda "invoiced" (no regresión)."""
        order = self._create_order(3.0)
        line = order.order_line
        self._validate(order.picking_ids)
        self._invoice(order)
        self.assertEqual(line.invoice_status, "invoiced")
