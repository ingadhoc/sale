from odoo.tests import TransactionCase
from odoo.exceptions import UserError

class TestActionCancel(TransactionCase):

    def setUp(self):
        super(TestActionCancel, self).setUp()

        # Crear una orden de venta y una línea de orden
        self.sale_order_model = self.env['sale.order']
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'type': 'consu'
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'customer_rank': 1,
        })
        self.sale_order = self.sale_order_model.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0
            })],
        })
        
        # Confirmar la orden de venta
        self.sale_order.action_confirm()

        # Crear una entrega
        self.picking = self.env['stock.picking'].search([('origin', '=', self.sale_order.name)], limit=1)
        self.picking._action_done()


    def test_action_cancel_without_deliveries(self):
        # Crear una nueva orden de venta sin entregas
        sale_order_without_deliveries = self.sale_order_model.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0
            })],
        })
        sale_order_without_deliveries.action_confirm()

        # Cancelar la orden sin entregas completadas
        sale_order_without_deliveries.action_cancel()
        wizard = self.env['sale.order.cancel'].with_context({'order_id': sale_order_without_deliveries.id}).create({'order_id': sale_order_without_deliveries.id})
        wizard.action_cancel()

        # Verificar el estado de la orden después de cancelar
        self.assertTrue(sale_order_without_deliveries.state == 'cancel')

    def test_action_cancel_context(self):
        # Crear una nueva orden de venta
        sale_order = self.sale_order_model.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0
            })],
        })
        sale_order.action_confirm()

        # Cancelar la orden desde el contexto con 'cancel_from_order=True'
        sale_order.with_context(cancel_from_order=True).action_cancel()
        wizard = self.env['sale.order.cancel'].with_context({'order_id': sale_order.id}).create({'order_id': sale_order.id})
        wizard.action_cancel()

        # Verificar el estado de la orden después de cancelar
        self.assertEqual(sale_order.state, 'cancel')
