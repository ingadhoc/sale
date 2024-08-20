##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import odoo.tests.common as common


<<<<<<< HEAD
@tagged('post_install', '-at_install')
class TestSaleOrderTypeAutomation(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company = cls.env.ref('l10n_ar.company_ri')
        cls.env.ref('base.user_admin').write({
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
        })
        tax = cls.env['account.tax'].search([('name', '=', '21%'), ('type_tax_use', '=', 'sale')], limit=1)
        product = cls.env["product.template"].create(
            {
                "name": "Test Product",
                "type": "product",
                "taxes_id": [(4, tax.id)]
            }
        )
        cls.env["stock.quant"].create(
            [
                {
                    "product_id": product.product_variant_id.id,
                    "location_id": cls.env.ref("stock.stock_location_stock").id,
                    "quantity": 30.0,
                },
            ]
        )
        cls.env["sale.order.type"].create(
            [
                {
                    "name": "Picking And Invoice Automation (Validate)",
                    "picking_atomation": "validate",
                    "invoicing_atomation": "validate_invoice",
                    "company_id": False,
                    "sequence": 1
                }
            ]
        )
        cls.env['exception.rule'].search([('active', '=', True)]).write({'active': False})

    def test_sale_order_type_automation(self):
        self.start_tour(
            "/",
            'sale_order_type_automation_tour',
            login="admin",
            step_delay=300,
        )

        sale_order_line = self.env['sale.order.line'].search([('product_id.name', '=', 'Test Product')], limit=1, order='id desc')
        self.assertTrue(sale_order_line, "No sale order line found for 'Test Product'")
||||||| parent of adf4c65e (temp)
@tagged('post_install', '-at_install')
class TestSaleOrderTypeAutomation(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company = cls.env.ref('l10n_ar.company_ri')
        cls.env.ref('base.user_admin').write({
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
        })
        tax = cls.env['account.tax'].search([('name', '=', 'IVA 21%'), ('type_tax_use', '=', 'sale')], limit=1)
        product = cls.env["product.template"].create(
            {
                "name": "Test Product",
                "type": "product",
                "taxes_id": [(4, tax.id)]
            }
        )
        cls.env["stock.quant"].create(
            [
                {
                    "product_id": product.product_variant_id.id,
                    "location_id": cls.env.ref("stock.stock_location_stock").id,
                    "quantity": 30.0,
                },
            ]
        )
        cls.env["sale.order.type"].create(
            [
                {
                    "name": "Picking And Invoice Automation (Validate)",
                    "picking_atomation": "validate",
                    "invoicing_atomation": "validate_invoice",
                    "company_id": False,
                    "sequence": 1
                }
            ]
        )

    def test_sale_order_type_automation(self):
        self.start_tour(
            "/",
            'sale_order_type_automation_tour',
            login="admin",
            step_delay=300,
        )

        sale_order_line = self.env['sale.order.line'].search([('product_id.name', '=', 'Test Product')], limit=1, order='id desc')
        self.assertTrue(sale_order_line, "No sale order line found for 'Test Product'")
=======
class TestSaleOrderTypeAutomation(common.TransactionCase):
>>>>>>> adf4c65e (temp)

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
