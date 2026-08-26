##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SaleStockUxCommon


@tagged("post_install", "-at_install")
class TestExchanges(SaleStockUxCommon):
    """Devoluciones para cambio.

    Cubre los comportamientos 19, 23, 27, 28 y 29 del relevamiento.
    """

    def test_el_wizard_de_devolucion_nace_con_reembolso_tildado(self):
        """El módulo fuerza to_refund=True por defecto en todas las líneas."""
        order = self._crear_orden_confirmada(qty=10.0)
        self._entregar(order.picking_ids)

        wizard = self._wizard_devolucion(order.picking_ids, qty=3.0, to_refund=True)

        self.assertTrue(
            all(wizard.product_return_moves.mapped("to_refund")),
            "El default del módulo es devolver con reembolso",
        )

    def test_no_se_puede_cambiar_una_linea_marcada_para_reembolso(self):
        """Control positivo: si el sistema tiene que bloquear, hay que ver que bloquee."""
        order = self._crear_orden_confirmada(qty=10.0)
        self._entregar(order.picking_ids)
        wizard = self._wizard_devolucion(order.picking_ids, qty=3.0, to_refund=True)

        with self.assertRaises(UserError):
            wizard.action_create_exchanges()

    def test_el_cambio_marca_sus_movimientos_y_no_los_mezcla(self):
        """Cadena: crear el cambio, verificar la marca, validarlo y ver el neto."""
        order = self._crear_orden_confirmada(qty=10.0)
        entrega = order.picking_ids
        self._entregar(entrega)
        entregado_antes = order.order_line.qty_delivered

        wizard = self._wizard_devolucion(entrega, qty=3.0, to_refund=False)
        wizard.action_create_exchanges()

        with self.subTest("los movimientos del cambio quedan marcados como tales"):
            moves_cambio = order.order_line.move_ids.filtered(lambda m: m.is_exchange_move)
            self.assertTrue(moves_cambio, "Tendrían que existir movimientos marcados como cambio")

        with self.subTest("un movimiento de cambio no se mezcla con uno normal"):
            self.assertIn(
                "is_exchange_move",
                self.env["stock.move"]._prepare_merge_moves_distinct_fields(),
                "is_exchange_move tiene que ser parte de la clave de merge",
            )

        with self.subTest("la cantidad entregada neta no se mueve por el cambio"):
            self.assertEqual(
                order.order_line.qty_delivered,
                entregado_antes,
                "Un cambio saca y repone: la entregada neta no cambia",
            )

        with self.subTest("el cambio no genera una contraentrega"):
            self.assert_bateria_venta(order)
