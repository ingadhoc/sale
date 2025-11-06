##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSaleOrderCancel(TransactionCase):
    """Test para validar la prohibición de cancelación de pedido de venta
    con factura validada"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear Cliente (res.partner)
        cls.partner_cliente = cls.env["res.partner"].create(
            {
                "name": "Deco Addict",
            }
        )

        # Crear Impuesto (account.tax)
        cls.impuesto_ventas = cls.env["account.tax"].create(
            {
                "name": "Impuesto 15% Ventas",
                "type_tax_use": "sale",
                "amount": 15.0,
            }
        )

        # Crear Producto (product.product)
        cls.producto_caja = cls.env["product.product"].create(
            {
                "name": "ECOMM Storage Box",
                "type": "consu",
                "list_price": 15.00,
                "taxes_id": [(6, 0, [cls.impuesto_ventas.id])],
            }
        )

    def test_cancelar_so_con_factura_validada_genera_error(self):
        """
        Test: Validar la lógica de negocio del backend que impide la cancelación
        de una orden de venta (sale.order) cuando esta tiene una factura de cliente
        (account.move) relacionada en estado "Publicado" (Posted).
        """
        # 1. Crear Pedido de Venta (Borrador)
        pedido_venta = self.env["sale.order"].create(
            {
                "partner_id": self.partner_cliente.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.producto_caja.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 15.00,
                        },
                    )
                ],
            }
        )

        # Verificar estado inicial (borrador)
        self.assertEqual(pedido_venta.state, "draft")

        # 2. Confirmar Pedido de Venta
        pedido_venta.action_confirm()

        # Validación: Estado después de confirmar
        self.assertEqual(
            pedido_venta.state, "sale", "El pedido de venta debe estar en estado 'sale' después de confirmar"
        )

        # 3. Crear Factura (Borrador) - Llamando directamente al método de backend
        factura_cliente = pedido_venta._create_invoices()

        # Verificar que se creó una factura
        self.assertTrue(factura_cliente, "Debe haberse creado una factura")
        self.assertEqual(len(factura_cliente), 1, "Debe haberse creado exactamente una factura")

        # Obtener el primer (y único) registro
        factura_cliente = factura_cliente[0]

        # Verificar que la factura está en borrador
        self.assertEqual(factura_cliente.state, "draft", "La factura debe estar en estado 'draft' al crearse")

        # 4. Validar (Publicar) Factura
        factura_cliente.action_post()

        # Validación: Estado de la factura después de publicar
        self.assertEqual(factura_cliente.state, "posted", "La factura debe estar en estado 'posted' después de validar")

        # Validación: Verificar que la factura está relacionada con el pedido
        self.assertIn(
            factura_cliente, pedido_venta.invoice_ids, "La factura debe estar relacionada con el pedido de venta"
        )

        # Validación: Verificar el estado de facturación del pedido
        self.assertEqual(
            pedido_venta.invoice_status, "invoiced", "El estado de facturación del pedido debe ser 'invoiced'"
        )

        # 5. Intentar Cancelar Pedido de Venta (Punto Crítico)
        # Este paso debe generar una excepción UserError
        with self.assertRaises(UserError) as context:
            pedido_venta.action_cancel()

        # Validación Opcional: Verificar el contenido del mensaje de error
        error_message = str(context.exception.args[0])
        self.assertIn("cancel", error_message.lower(), "El mensaje de error debe mencionar que no se puede cancelar")

        # Validación: Verificar que el estado del pedido no cambió
        self.assertEqual(
            pedido_venta.state,
            "sale",
            "El pedido debe permanecer en estado 'sale' después del intento fallido de cancelación",
        )
