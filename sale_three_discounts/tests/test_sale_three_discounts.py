##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSaleThreeDiscounts(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company = cls.env.ref('l10n_ar.company_ri')
        cls.env.ref('base.user_admin').write({
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
        })
        tax = cls.env['account.tax'].search([('name', '=', '21%'), ('type_tax_use', '=', 'sale')], limit=1)
        cls.env["product.product"].create(
            {
                "name": "Test Product 1",
                "type": "consu",
                "taxes_id": [(4, tax.id)],
                'list_price': 100
            }
        )
        cls.env["product.pricelist"].create([
            {
                "name": "Pricelist with discount",
                "company_id": cls.env.company.id,
                "discount_policy": "with_discount",
                "currency_id": cls.env.company.currency_id.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "3_global",
                            "compute_price": "percentage",
                            "percent_price": 15
                        },
                    )
                ],
            },
            {
                "name": "Pricelist without discount",
                "company_id": cls.env.company.id,
                "discount_policy": "without_discount",
                "currency_id": cls.env.company.currency_id.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "3_global",
                            "compute_price": "percentage",
                            "percent_price": 15
                        },
                    )
                ],
            }
        ])

    def test_sale_three_discounts(self):
        self.start_tour(
            "/",
            'sale_three_discounts_tour',
            login="admin",
            step_delay=100
        )
