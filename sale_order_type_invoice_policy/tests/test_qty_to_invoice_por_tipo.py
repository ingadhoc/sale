##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged

from .common import SaleOrderTypeInvoicePolicyCommon


@tagged("post_install", "-at_install")
class TestQtyToInvoicePorTipo(SaleOrderTypeInvoicePolicyCommon):
    """La política de facturación del tipo de venta manda sobre la del producto.

    Cubre: ordenadas y prepago facturan lo ordenado menos lo devuelto, entregadas
    factura lo entregado, y "la define el producto" deja el cálculo nativo intacto.
    """

    def test_politica_del_tipo_pisa_la_del_producto(self):
        # el producto factura por entregadas: cada tipo tiene que torcer eso o no
        casos = [
            ("order", 10.0, "ordenadas: factura lo pedido aunque no se haya entregado"),
            ("prepaid", 10.0, "prepago: factura lo pedido"),
            ("prepaid_block_delivery", 10.0, "prepago con entrega bloqueada: factura lo pedido"),
            ("delivery", 4.0, "entregadas: factura solo lo entregado"),
            ("by_product", 4.0, "la define el producto: queda el nativo, que es entregadas"),
        ]
        for invoice_policy, esperado, etiqueta in casos:
            with self.subTest(etiqueta):
                order = self._order(self._sale_type(invoice_policy))
                self._deliver(order.picking_ids, qty=4.0)
                self.assertEqual(order.order_line.qty_delivered, 4.0)
                self.assertEqual(order.order_line.qty_to_invoice, esperado)
                self.assert_invariantes(order)

    def test_sin_tipo_queda_la_politica_del_producto(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 10.0, "price_unit": 100.0})],
            }
        )
        order.action_confirm()
        self._deliver(order.picking_ids, qty=4.0)
        self.assertEqual(order.order_line.qty_to_invoice, 4.0)
        self.assert_invariantes(order)

    def test_lo_facturado_se_descuenta_en_cada_politica(self):
        for invoice_policy, esperado in [("order", 6.0), ("delivery", 0.0)]:
            with self.subTest(invoice_policy):
                order = self._order(self._sale_type(invoice_policy))
                self._deliver(order.picking_ids, qty=4.0)
                invoice = order._create_invoices()
                invoice.invoice_line_ids.quantity = 4.0
                invoice.action_post()
                self.assertEqual(order.order_line.qty_invoiced, 4.0)
                self.assertEqual(order.order_line.qty_to_invoice, esperado)
                self.assert_invariantes(order)

    def test_la_venta_sin_confirmar_no_tiene_nada_por_facturar(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "type_id": self._sale_type("order").id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 10.0, "price_unit": 100.0})],
            }
        )
        self.assertEqual(order.order_line.qty_to_invoice, 0.0)
        self.assert_invariantes(order)
