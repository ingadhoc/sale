##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SaleStockUxCommon


@tagged("post_install", "-at_install")
class TestDeliveryStatus(SaleStockUxCommon):
    """Estado de entrega forzado y bloqueo de cancelación.

    Cubre los comportamientos 1, 2, 3, 4 y 5 del relevamiento.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Un usuario interno de ventas, sin permisos de administración: es el
        # que tiene que rebotar contra el control de force_delivery_status
        cls.usuario_ventas = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Vendedor Sale Stock UX",
                    "login": "vendedor@salestockux.test",
                    "email": "vendedor@salestockux.test",
                    "company_id": cls.env.company.id,
                    "company_ids": [Command.set(cls.env.company.ids)],
                    "group_ids": [Command.set([cls.env.ref("sales_team.group_sale_manager").id])],
                }
            )
        )

    def test_solo_un_administrador_puede_forzar_el_estado_de_entrega(self):
        """Control positivo en los dos caminos: create y write."""
        order = self._crear_orden_confirmada(qty=10.0)
        self.assertFalse(
            self.usuario_ventas.has_group("base.group_system"),
            "El escenario necesita un usuario sin permisos de administración",
        )

        with self.subTest("el usuario sí puede escribir la orden"):
            # Sin este paso el test pasaría por un AccessError, que en Odoo
            # también es un UserError: verificaría permisos, no el control
            order.with_user(self.usuario_ventas).write({"client_order_ref": "REF-OK"})
            self.assertEqual(order.client_order_ref, "REF-OK")

        with self.subTest("pero no puede forzar el estado de entrega al escribir"):
            with self.assertRaises(UserError) as capturado:
                order.with_user(self.usuario_ventas).write({"force_delivery_status": "full"})
            self.assertIn(
                "Set Delivered",
                str(capturado.exception),
                "Tiene que rebotar por el control del módulo, no por falta de permisos",
            )

        with self.subTest("tampoco al crear la orden"):
            with self.assertRaises(UserError) as capturado:
                self.env["sale.order"].with_user(self.usuario_ventas).create(
                    {"partner_id": self.partner_a.id, "force_delivery_status": "full"}
                )
            self.assertIn("Set Delivered", str(capturado.exception))

    def test_el_estado_forzado_pisa_el_de_la_orden_y_el_de_la_linea(self):
        """Forzado por un administrador, gana sobre lo que diga el cálculo."""
        order = self._crear_orden_confirmada(qty=10.0)
        self.assertTrue(order.picking_ids, "El escenario necesita una entrega viva")
        self.assertEqual(order.order_line.delivery_status, "to deliver")

        order.force_delivery_status = "full"

        with self.subTest("pisa el estado de la orden"):
            self.assertEqual(order.delivery_status, "full")
        with self.subTest("pisa el estado de la línea"):
            self.assertEqual(order.order_line.delivery_status, "full")
        self.assert_bateria_venta(order)

    def test_no_se_puede_cancelar_una_orden_con_una_entrega_hecha(self):
        """Cadena: cancelar sin entregas, con entrega hecha, y el estado resultante."""
        sin_entregas = self._crear_orden_confirmada(qty=10.0)

        with self.subTest("una orden sin entregas hechas se cancela"):
            sin_entregas.action_cancel()
            self.assertEqual(sin_entregas.state, "cancel")

        with self.subTest("cancelada, el estado de entrega vuelve a 'nada por entregar'"):
            self.assertEqual(sin_entregas.delivery_status, "no")

        with self.subTest("una orden con una entrega hecha no se puede cancelar"):
            entregada = self._crear_orden_confirmada(qty=10.0)
            self._entregar(entregada.picking_ids)
            with self.assertRaises(UserError):
                entregada.action_cancel()
            self.assertEqual(entregada.state, "sale", "La orden tiene que seguir viva")
