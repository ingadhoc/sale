##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged

from .common import SaleStockUxCommon


@tagged("post_install", "-at_install")
class TestCancelRemaining(SaleStockUxCommon):
    """Cancelar remanente: la cantidad pedida baja a lo efectivamente movido.

    Cubre los comportamientos 7, 11, 14, 15, 22 y 30 del relevamiento. El 16
    (recursión en packs detallados, sale_order_line.py:150) queda declarado sin
    implementar: necesita `product_pack` instalado, que no está en el `depends`
    de este módulo.
    """

    def test_cancelar_remanente_baja_la_cantidad_a_lo_entregado(self):
        """Cadena: confirmar, entregar parcial, cancelar remanente, y volver a subir."""
        order = self._crear_orden_confirmada(qty=10.0)
        entrega = order.picking_ids
        self.assert_bateria_venta(order)

        with self.subTest("entregada una parte, la línea sigue por entregar"):
            self._entregar(entrega, qty=4.0)
            self.assertEqual(order.order_line.qty_delivered, 4.0)
            self.assertEqual(order.order_line.delivery_status, "to deliver")
            self.assert_bateria_venta(order)

        with self.subTest("cancelar remanente deja la línea en lo efectivamente entregado"):
            order.order_line.button_cancel_remaining()
            self.assertEqual(order.order_line.product_uom_qty, 4.0)
            self.assert_bateria_venta(order)

        with self.subTest("la línea queda entregada por completo"):
            self.assertEqual(order.order_line.delivery_status, "full")

        with self.subTest("no queda demanda viva pendiente"):
            vivos = order.order_line.move_ids.filtered(lambda m: m.state not in ("done", "cancel"))
            self.assertFalse(vivos, "Quedaron moves pendientes tras cancelar el remanente")

        with self.subTest("queda registro en el chatter de la orden"):
            cuerpos = order.message_ids.mapped("body")
            self.assertTrue(
                any("Cancel remaining" in str(cuerpo) for cuerpo in cuerpos),
                "Cancelar remanente tiene que dejar el movimiento asentado en el chatter",
            )

        with self.subTest("volver a subir la cantidad genera entrega nueva, no una contraentrega"):
            order.order_line.product_uom_qty = 9.0
            self.assert_bateria_venta(order)

    def test_cancelar_remanente_destilda_los_remitos_ya_impresos(self):
        """Un picking impreso se destilda: si no, Odoo mezcla moves y genera contraentrega."""
        order = self._crear_orden_confirmada(qty=10.0)
        self._entregar(order.picking_ids, qty=4.0)
        pendiente = order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
        pendiente.printed = True

        order.order_line.button_cancel_remaining()

        self.assertFalse(pendiente.printed, "El picking pendiente tiene que quedar destildado")
        self.assert_bateria_venta(order)

    def test_cancelar_remanente_respeta_la_orden_bloqueada(self):
        """Una orden bloqueada se destraba para escribir y vuelve a quedar bloqueada."""
        order = self._crear_orden_confirmada(qty=10.0)
        self._entregar(order.picking_ids, qty=4.0)
        order.locked = True

        order.order_line.button_cancel_remaining()

        self.assertEqual(order.order_line.product_uom_qty, 4.0, "La cantidad tiene que haberse escrito igual")
        self.assertTrue(order.locked, "La orden tiene que volver a quedar bloqueada")
        self.assert_bateria_venta(order)

    def test_el_wizard_masivo_toca_solo_las_lineas_por_entregar(self):
        """El wizard cancela el remanente de las líneas en 'to deliver', y solo esas."""
        order = self._crear_orden_confirmada(qty=10.0)
        self._entregar(order.picking_ids)
        self.assertEqual(order.order_line.delivery_status, "full")
        cantidad_previa = order.order_line.product_uom_qty

        wizard = (
            self.env["sale.order.cancel.remaining"]
            .with_context(active_ids=order.ids, active_model="sale.order")
            .create({})
        )
        wizard.action_confirm()

        self.assertEqual(
            order.order_line.product_uom_qty,
            cantidad_previa,
            "Una línea ya entregada por completo no la tiene que tocar el wizard",
        )
        self.assert_bateria_venta(order)
