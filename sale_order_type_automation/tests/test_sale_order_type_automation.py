##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import odoo.tests.common as common


class TestSaleOrderTypeAutomation(common.TransactionCase):

    def setUp(self):
        # TODO mejorar los tests
        super().setUp()
        self.sale_order_model = self.env['sale.order']
        self.sale_order_type = self.env.ref('sale_order_type.normal_sale_type')
        self.sequence = self.env['ir.sequence'].create({
            'name': 'Test Sales Order 2',
            'code': 'sale.order',
            'prefix': 'TSO2',
            'padding': 3,
            'company_id': self.sale_order_type.warehouse_id.company_id.id,
        })
        self.partner = self.env.ref('base.res_partner_1')
        self.product = self.env.ref('product.product_product_4')
        self.payment_journal = self.env[
            'account.journal'].search(
                [('type', '=', 'cash')], limit=1)
        self.sale_type = self.sale_order_type.write({
            # 'validate_automatically_picking': True,
            # 'validate_automatically_invoice': True,
            # 'validate_automatically_payment': True,
            # 'payment_journal_id': self.payment_journal.id,
            'sequence_id': self.sequence.id,
        })

    def test_sale_order_confirm(self):
        sale_line_dict = {
            'product_id': self.product.id,
            'name': self.product.name,
            'product_uom_qty': 1.0,
            'product_uom': self.product.uom_id.id,
            'price_unit': self.product.list_price,
        }
        vals = {
            'partner_id': self.partner.id,
            'type_id': self.sale_order_type.id,
            'order_line': [(0, 0, sale_line_dict)]
        }
        sale_order = self.sale_order_model.create(vals)
        sale_order.action_confirm()

    def test_pay_automation_wo_payment_pro(self):
        company = self.env['res.company'].search([('use_payment_pro', '=', False)], limit=1)
        self.env.company = company

        automatic_sale_order_type = self.sale_order_type.copy()
        automatic_sale_order_type.write({
            'picking_atomation':  'validate',
            'invoicing_atomation': 'validate_invoice',
            'payment_atomation': 'validate_payment',
            'journal_id': self.env.ref('account.1_sale'),
            'payment_journal_id': self.env.ref('account.1_cash')
        })

        sale_order = self.sale_order_model.create({
                    'partner_id': self.partner.id,
                    'type_id': automatic_sale_order_type.id,
                    'order_line': [
                        (0, 0, {
                            'product_id': self.product.id,
                            'name': self.product.name,
                            'product_uom_qty': 1,
                            'price_unit': 100,
                        }),
                    ],
                })

        sale_order.action_confirm()

        payment_amount = sale_order.invoice_ids.invoice_payments_widget['content'][0]['amount']
        invoice_amount = sale_order.invoice_ids.amount_total
        self.assertEqual(invoice_amount, payment_amount, "No se generó correctamente el pago automático en una compañía sin payment_pro")
