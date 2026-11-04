from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestInvoiceStatusReturn(AccountTestInvoicingCommon):
    """Facturación de las devoluciones en 20: la de Odoo, sin descontar lo devuelto.

    Con política "según lo pedido", lo devuelto ya no se resta de lo que se
    factura: un cambio (Exchange) no deja una nota de crédito pendiente, y una
    devolución sin reposición se abona a mano. Con "según lo entregado", Odoo
    descuenta la devolución de lo entregado y pide la nota de crédito, como
    siempre.
    """

    @classmethod
    def get_default_groups(cls):
        # El usuario de AccountTestInvoicingCommon no trae grupos de ventas y no
        # puede crear la orden del escenario.
        return super().get_default_groups() | cls.quick_ref("sales_team.group_sale_manager")

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

    def _create_order(self, qty, product=None):
        product = product or self.product
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": qty, "price_unit": 100.0})],
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
        # En 20 la devolución es un albarán en borrador (sin asistente) y devuelve "para abonar" por defecto.
        returned = self.env["stock.picking"].browse(picking.action_return()["res_id"])
        returned.move_ids.product_uom_qty = quantity
        self._validate(returned)
        return returned

    def _invoice(self, order):
        invoices = order._create_invoices(final=True)
        invoices.action_post()
        return invoices

    def test_partial_return_keeps_ordered_billed(self):
        """Según lo pedido: devolver 1 de 2 no deja nada a facturar ni a acreditar."""
        order = self._create_order(2.0)
        line = order.order_line
        delivery = order.picking_ids
        self._validate(delivery)
        self._invoice(order)

        self._make_return(delivery, quantity=1.0)

        self.assertEqual(line.quantity_returned, 1.0)
        self.assertEqual(line.qty_to_invoice, 0.0)
        self.assertEqual(line.invoice_status, "invoiced")
        self.assertAlmostEqual(line.amount_to_invoice, 0.0, places=2)

    def test_exchange_leaves_nothing_to_invoice(self):
        """Según lo pedido: devolver 2 de 10 y cambiarlas no deja una nota de crédito pendiente."""
        order = self._create_order(10.0)
        line = order.order_line
        delivery = order.picking_ids
        self._validate(delivery)
        self._invoice(order)

        returned = self._make_return(delivery, quantity=2.0)
        exchange = self.env["stock.picking"].browse(returned.action_exchange()["res_id"])
        self._validate(exchange)

        self.assertEqual(line.qty_delivered, 10.0)
        self.assertEqual(line.qty_to_invoice, 0.0)
        self.assertEqual(line.invoice_status, "invoiced")
        self.assertAlmostEqual(line.amount_to_invoice, 0.0, places=2)

    def test_delivered_policy_return_asks_credit_note(self):
        """Según lo entregado: la devolución queda a acreditar, como en Odoo."""
        product = self.product.copy({"invoice_policy": "delivery"})
        order = self._create_order(2.0, product=product)
        line = order.order_line
        delivery = order.picking_ids
        self._validate(delivery)
        self._invoice(order)

        self._make_return(delivery, quantity=1.0)

        self.assertEqual(line.qty_to_invoice, -1.0)
        self.assertEqual(line.invoice_status, "to invoice")
