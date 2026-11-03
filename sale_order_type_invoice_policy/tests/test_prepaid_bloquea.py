##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SaleOrderTypeInvoicePolicyCommon


@tagged("post_install", "-at_install")
class TestPrepaidBloquea(SaleOrderTypeInvoicePolicyCommon):
    """Con política prepago, la salida no se reserva ni se valida hasta que la venta
    está facturada y cobrada. Recorre la cadena completa: bloqueado, cobro, liberado."""

    def _cobrar(self, order):
        invoice = order._create_invoices()
        invoice.action_post()
        self.env["account.payment.register"].with_context(active_model="account.move", active_ids=invoice.ids).create(
            {"payment_date": invoice.invoice_date}
        )._create_payments()
        return invoice

    def test_prepago_bloquea_hasta_el_cobro(self):
        order = self._order(self._sale_type("prepaid"))
        picking = order.picking_ids
        picking.action_confirm()

        with self.subTest("sin cobrar, reservar no asigna nada"):
            picking.action_assign()
            self.assertEqual(picking.state, "confirmed")
            self.assertFalse(picking.move_ids.picked)

        with self.subTest("sin cobrar, con prepaid_raise reservar avisa"):
            with self.assertRaises(UserError):
                picking.with_context(prepaid_raise=True).action_assign()

        with self.subTest("sin cobrar, validar la salida avisa"):
            with self.assertRaises(UserError):
                picking.button_validate()

        with self.subTest("facturada y cobrada, la salida se reserva y se valida"):
            self._cobrar(order)
            self.assertEqual(order.invoice_status, "invoiced")
            picking.action_assign()
            self.assertEqual(picking.state, "assigned")
            self._deliver(picking)
            self.assertEqual(picking.state, "done")

        self.assert_invariantes(order)

    def test_prepaid_block_delivery_no_bloquea_la_reserva(self):
        """Esta política bloquea solo la validación: la reserva tiene que seguir andando."""
        order = self._order(self._sale_type("prepaid_block_delivery"))
        picking = order.picking_ids
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(picking.state, "assigned")
        with self.assertRaises(UserError):
            picking.button_validate()
        self.assert_invariantes(order)

    def test_sin_prepago_la_salida_no_se_bloquea(self):
        order = self._order(self._sale_type("delivery"))
        picking = order.picking_ids
        self._deliver(picking)
        self.assertEqual(picking.state, "done")
        self.assert_invariantes(order)

    def test_el_cron_de_reserva_saltea_las_salidas_prepagas(self):
        """_action_assign de stock.move es el que corre el cron: saca los movimientos
        de una salida prepaga impaga en vez de reservarlos."""
        prepago = self._order(self._sale_type("prepaid"))
        comun = self._order(self._sale_type("delivery"))
        movimientos = (prepago.picking_ids | comun.picking_ids).move_ids
        movimientos.picking_id.action_confirm()

        movimientos._action_assign()

        self.assertEqual(prepago.picking_ids.state, "confirmed")
        self.assertEqual(comun.picking_ids.state, "assigned")
        self.assert_invariantes(prepago)
        self.assert_invariantes(comun)
