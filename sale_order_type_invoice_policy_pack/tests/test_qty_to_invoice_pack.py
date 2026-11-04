##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale_order_type_invoice_policy.tests.common import SaleOrderTypeInvoicePolicyCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestQtyToInvoicePack(SaleOrderTypeInvoicePolicyCommon):
    """Con la política "entregadas" del tipo de venta, un pack se factura por el
    componente menos entregado, no por lo entregado de la línea del pack."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.component_a = cls._storable("Pack Component A")
        cls.component_b = cls._storable("Pack Component B")
        # 2 de A y 1 de B por pack: así cada componente da otra cantidad de packs
        cls.pack = cls.env["product.product"].create(
            {
                "name": "Invoice Policy Pack",
                "type": "consu",
                "is_storable": False,
                "invoice_policy": "delivery",
                "list_price": 500.0,
                "pack_ok": True,
                "pack_type": "detailed",
                "pack_component_price": "totalized",
                "pack_line_ids": [
                    (0, 0, {"product_id": cls.component_a.id, "quantity": 2.0}),
                    (0, 0, {"product_id": cls.component_b.id, "quantity": 1.0}),
                ],
            }
        )

    @classmethod
    def _storable(cls, name):
        product = cls.env["product.product"].create(
            {"name": name, "type": "consu", "is_storable": True, "list_price": 100.0}
        )
        cls.env["stock.quant"]._update_available_quantity(product, cls.warehouse.lot_stock_id, 1000.0)
        return product

    def _pack_lines(self, order):
        parent = order.order_line.filtered(lambda sol: sol.pack_child_line_ids)
        return parent, parent.pack_child_line_ids

    def _deliver_components(self, order, qty_by_product):
        picking = order.picking_ids
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = qty_by_product.get(move.product_id, move.product_uom_qty)
        picking.move_ids.picked = True
        picking.with_context(cancel_backorder=True)._action_done()

    def test_el_pack_se_factura_por_el_componente_menos_entregado(self):
        order = self._order(self._sale_type("delivery"), qty=10.0, product=self.pack)
        parent, children = self._pack_lines(order)
        self.assertEqual(len(children), 2, "el pack detallado tiene que abrir sus dos componentes")
        # A: 12 de 20 -> 6 packs; B: 10 de 10 -> 10 packs. Manda el menor.
        self._deliver_components(order, {self.component_a: 12.0, self.component_b: 10.0})
        self.assertEqual(parent.qty_to_invoice, 6.0)
        self.assert_invariantes(order)

    def test_lo_facturado_del_pack_se_descuenta(self):
        order = self._order(self._sale_type("delivery"), qty=10.0, product=self.pack)
        parent, dummy = self._pack_lines(order)
        self._deliver_components(order, {self.component_a: 12.0, self.component_b: 10.0})
        invoice = order._create_invoices()
        invoice.invoice_line_ids.filtered(lambda line: line.product_id == self.pack).quantity = 6.0
        invoice.action_post()
        self.assertEqual(parent.qty_invoiced, 6.0)
        self.assertEqual(parent.qty_to_invoice, 0.0)
        self.assert_invariantes(order)

    def test_sin_entregar_ningun_componente_no_hay_nada_por_facturar(self):
        order = self._order(self._sale_type("delivery"), qty=10.0, product=self.pack)
        parent, dummy = self._pack_lines(order)
        self.assertEqual(parent.qty_to_invoice, 0.0)
        self.assert_invariantes(order)

    def test_con_otra_politica_el_pack_no_se_toca(self):
        # "ordenadas" la resuelve el módulo padre: el puente no tiene que meterse
        order = self._order(self._sale_type("order"), qty=10.0, product=self.pack)
        parent, dummy = self._pack_lines(order)
        self._deliver_components(order, {self.component_a: 12.0, self.component_b: 10.0})
        self.assertEqual(parent.qty_to_invoice, 10.0)
        self.assert_invariantes(order)
