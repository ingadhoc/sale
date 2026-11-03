##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale_order_type_invoice_policy.tests.common import SaleOrderTypeInvoicePolicyCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestServicesDelivered(SaleOrderTypeInvoicePolicyCommon):
    """Con "Excluir servicios prepagos" activo, un tipo de venta por entregadas deja de
    aplicar esa política a los servicios que se cobran por adelantado."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.servicio_prepago = cls.env["product.product"].create(
            {
                "name": "Servicio prepago",
                "type": "service",
                "invoice_policy": "order",
                "service_type": "manual",
                "list_price": 100.0,
            }
        )
        cls.servicio_entregado = cls.env["product.product"].create(
            {
                "name": "Servicio por entregadas",
                "type": "service",
                "invoice_policy": "delivery",
                "service_type": "manual",
                "list_price": 100.0,
            }
        )

    def setUp(self):
        super().setUp()
        self.assertEqual(self.servicio_prepago.service_policy, "ordered_prepaid")

    def _venta_de_servicio(self, services_delivered, producto):
        sale_type = self._sale_type("delivery", services_delivered=services_delivered)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "type_id": sale_type.id,
                "order_line": [(0, 0, {"product_id": producto.id, "product_uom_qty": 10.0, "price_unit": 100.0})],
            }
        )
        order.action_confirm()
        order.order_line.qty_delivered = 4.0
        return order

    def test_el_servicio_prepago_queda_afuera_de_la_politica_por_entregadas(self):
        order = self._venta_de_servicio(True, self.servicio_prepago)
        self.assertEqual(order.order_line.qty_to_invoice, 10.0)
        self.assert_invariantes(order)

    def test_sin_el_flag_el_servicio_prepago_sigue_la_politica_del_tipo(self):
        order = self._venta_de_servicio(False, self.servicio_prepago)
        self.assertEqual(order.order_line.qty_to_invoice, 4.0)
        self.assert_invariantes(order)

    def test_el_flag_no_toca_un_servicio_que_no_es_prepago(self):
        order = self._venta_de_servicio(True, self.servicio_entregado)
        self.assertEqual(order.order_line.qty_to_invoice, 4.0)
        self.assert_invariantes(order)

    def test_el_flag_no_toca_un_producto_almacenable(self):
        order = self._order(self._sale_type("delivery", services_delivered=True))
        self._deliver(order.picking_ids, qty=4.0)
        self.assertEqual(order.order_line.qty_to_invoice, 4.0)
        self.assert_invariantes(order)

    def test_lo_facturado_se_descuenta_en_el_servicio_prepago(self):
        order = self._venta_de_servicio(True, self.servicio_prepago)
        invoice = order._create_invoices()
        invoice.invoice_line_ids.quantity = 6.0
        invoice.action_post()
        self.assertEqual(order.order_line.qty_invoiced, 6.0)
        self.assertEqual(order.order_line.qty_to_invoice, 4.0)
        self.assert_invariantes(order)
