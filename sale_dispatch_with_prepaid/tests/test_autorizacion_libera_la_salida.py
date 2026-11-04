##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale_order_type_invoice_policy.tests.common import SaleOrderTypeInvoicePolicyCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAutorizacionLiberaLaSalida(SaleOrderTypeInvoicePolicyCommon):
    """El check de la venta deja reservar y despachar una salida prepaga impaga.

    Recorre la cadena sobre una venta con política `prepaid`, que es la que bloquea
    las dos operaciones: sin autorizar la salida sigue bloqueada (control positivo:
    el módulo no tiene que apagar el bloqueo para todos), y con la autorización se
    reserva y se entrega sin que medie factura.
    """

    def test_la_autorizacion_libera_la_salida_prepaga(self):
        order = self._order(self._sale_type("prepaid"))
        picking = order.picking_ids
        picking.action_confirm()

        with self.subTest("sin autorizar, la salida prepaga no se reserva"):
            picking.action_assign()
            self.assertEqual(picking.state, "confirmed")

        with self.subTest("sin autorizar, validar la salida prepaga avisa"):
            with self.assertRaises(UserError):
                picking.button_validate()

        order.approve_picking = True

        with self.subTest("autorizada, la salida prepaga se reserva"):
            picking.action_assign()
            self.assertEqual(picking.state, "assigned")

        with self.subTest("autorizada, la salida prepaga se entrega sin factura"):
            self._deliver(picking)
            self.assertEqual(picking.state, "done")
            self.assertFalse(order.invoice_ids)

        self.assert_invariantes(order)
