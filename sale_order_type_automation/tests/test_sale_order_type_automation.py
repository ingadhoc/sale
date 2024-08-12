##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import HttpCase, tagged


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

        if sale_order_line:
            sale_order = sale_order_line.order_id
            self.assertEqual(sale_order.state, 'sale', "Sale order is not in 'sale' state")

            self.assertEqual(len(sale_order.picking_ids), 1, "There should be exactly one picking associated with the sale order")
            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.state, 'done', "The picking is not in 'done' state")

            self.assertEqual(len(sale_order.invoice_ids), 1, "There should be exactly one invoice associated with the sale order")
            invoice = sale_order.invoice_ids[0]
            self.assertEqual(invoice.state, 'posted', "The invoice is not in 'posted' state")
