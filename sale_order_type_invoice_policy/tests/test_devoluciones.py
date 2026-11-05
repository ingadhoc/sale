##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged

from .common import SaleOrderTypeInvoicePolicyCommon


@tagged("post_install", "-at_install")
class TestDevoluciones(SaleOrderTypeInvoicePolicyCommon):
    """Las devoluciones se facturan como en Odoo: lo devuelto no se resta.

    Con una política del tipo que factura lo pedido, una devolución no deja una
    nota de crédito pendiente, ni siquiera cuando se repone con un cambio. Con
    "entregadas" queda el cálculo nativo, que sí pide la nota de crédito.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # entrega en un paso: así order.picking_ids es la salida y nada más
        cls.warehouse.delivery_steps = "ship_only"

    def _facturar(self, order):
        invoice = order._create_invoices(final=True)
        invoice.action_post()
        return invoice

    def _devolver(self, picking, qty):
        # en 20 la devolución es un albarán en borrador, sin asistente
        returned = self.env["stock.picking"].browse(picking.action_return()["res_id"])
        returned.move_ids.product_uom_qty = qty
        self._deliver(returned)
        return returned

    def _cambiar(self, returned):
        exchange = self.env["stock.picking"].browse(returned.action_exchange()["res_id"])
        self._deliver(exchange)
        return exchange

    def test_devolucion_no_se_resta_de_lo_que_se_factura(self):
        for invoice_policy in ["order", "prepaid", "prepaid_block_delivery"]:
            with self.subTest(invoice_policy):
                order = self._order(self._sale_type(invoice_policy))
                self._deliver(order.picking_ids)
                self._facturar(order)

                self._devolver(order.picking_ids, qty=2.0)

                line = order.order_line
                self.assertEqual(line.quantity_returned, 2.0)
                self.assertEqual(line.qty_invoiced, 10.0)
                self.assertEqual(line.qty_to_invoice, 0.0, "lo devuelto no se acredita solo")
                self.assertEqual(line.invoice_status, "invoiced")
                self.assert_invariantes(order)

    def test_el_cambio_no_deja_una_nota_de_credito_pendiente(self):
        for invoice_policy in ["order", "prepaid", "prepaid_block_delivery"]:
            with self.subTest(invoice_policy):
                order = self._order(self._sale_type(invoice_policy))
                delivery = order.picking_ids
                self._deliver(delivery)
                self._facturar(order)

                returned = self._devolver(delivery, qty=2.0)
                self._cambiar(returned)

                line = order.order_line
                self.assertEqual(line.qty_delivered, 10.0, "el cambio repone lo devuelto")
                self.assertEqual(line.qty_to_invoice, 0.0, "el cliente recibió el reemplazo: no se le acredita")
                self.assertEqual(line.invoice_status, "invoiced")
                self.assert_invariantes(order)

    def test_entregadas_pide_la_nota_de_credito(self):
        order = self._order(self._sale_type("delivery"))
        self._deliver(order.picking_ids)
        self._facturar(order)

        self._devolver(order.picking_ids, qty=2.0)

        line = order.order_line
        self.assertEqual(line.qty_delivered, 8.0)
        self.assertEqual(line.qty_to_invoice, -2.0)
        self.assertEqual(line.invoice_status, "to invoice")
        self.assert_invariantes(order)
