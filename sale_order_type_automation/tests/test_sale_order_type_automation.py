# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import openerp.tests.common as common


class TestSaleOrderTypeAutomation(common.TransactionCase):

    def setUp(self):
        super(TestSaleOrderTypeAutomation, self).setUp()
        self.sale_order_model = self.env['sale.order']
        self.partner = self.env.ref('base.res_partner_1')
        self.sale_order_type = self.env.ref('sale_order_type.normal_sale_type')
        self.product = self.env.ref('product.product_product_4')
        self.sale_order_type.validate_automatically_picking = True
        self.sale_order_type.validate_automatically_invoice = True
        self.sale_order_type.validate_automatically_payment = True
        self.sale_order_type.payment_journal_id = self.env['account.journal']\
            .search([('type', '=', 'sale')], limit=1)

    def test_sale_order_confirm(self):
        sale_line_dict = {
            'product_id': self.product.id,
            'name': self.product.name,
            'product_uom_qty': 1.0,
            'price_unit': self.product.lst_price,
        }
        vals = {
            'partner_id': self.partner.id,
            'partner_id': self.partner.id,
            'order_line': [(0, 0, sale_line_dict)]
        }
        sale_order = self.sale_order_model.create(vals)
        sale_order.action_confirm()
