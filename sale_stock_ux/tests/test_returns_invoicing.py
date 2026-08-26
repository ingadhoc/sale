##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged

from .common import SaleStockUxCommon


@tagged("post_install", "-at_install")
class TestReturnsInvoicing(SaleStockUxCommon):
    """Devolución con reembolso y su efecto sobre la facturación.

    Cubre los comportamientos 6, 8, 10, 11, 12 y 13 del relevamiento. Es el
    mecanismo del que salió la reapertura del ticket 123997: con política por
    lo pedido, lo devuelto tiene que descontarse de lo facturable o la orden
    queda "por facturar" para siempre.
    """

    def test_devolucion_con_reembolso_descuenta_lo_facturable(self):
        """Cadena: entregar todo, devolver con reembolso, facturar el resto."""
        order = self._crear_orden_confirmada(qty=10.0)
        self.assertEqual(order.order_line.product_id.invoice_policy, "order")
        self._entregar(order.picking_ids)
        self.assert_bateria_venta(order)

        with self.subTest("entregada la orden, hay 10 por facturar"):
            self.assertEqual(order.order_line.qty_to_invoice, 10.0)

        with self.subTest("la devolución con reembolso suma a la cantidad devuelta"):
            wizard = self._wizard_devolucion(order.picking_ids, qty=3.0, to_refund=True)
            devolucion = self.env["stock.picking"].browse(wizard.action_create_returns()["res_id"])
            self._entregar(devolucion)
            self.assertEqual(order.order_line.quantity_returned, 3.0)
            self.assert_bateria_venta(order)

        with self.subTest("la orden queda marcada como que tiene devoluciones"):
            self.assertTrue(order.with_returns)

        with self.subTest("con política por lo pedido, lo devuelto sale de lo facturable"):
            self.assertEqual(
                order.order_line.qty_to_invoice,
                7.0,
                "Tienen que quedar 10 - 3 devueltas por facturar",
            )

        with self.subTest("facturado el resto, la orden no queda 'por facturar'"):
            factura = order._create_invoices()
            factura.action_post()
            self.assertEqual(order.order_line.qty_invoiced, 7.0)
            self.assertEqual(order.order_line.invoice_status, "invoiced")
            self.assert_bateria_venta(order)

    def test_la_devolucion_sin_reembolso_no_toca_lo_facturable(self):
        """Espejo del anterior: sin reembolso, lo devuelto no descuenta."""
        order = self._crear_orden_confirmada(qty=10.0)
        self._entregar(order.picking_ids)

        wizard = self._wizard_devolucion(order.picking_ids, qty=3.0, to_refund=False)
        devolucion = self.env["stock.picking"].browse(wizard.action_create_returns()["res_id"])
        self._entregar(devolucion)

        self.assertEqual(order.order_line.quantity_returned, 0.0, "Sin reembolso no cuenta como devuelta")
        self.assertEqual(order.order_line.qty_to_invoice, 10.0)
        self.assert_bateria_venta(order)
