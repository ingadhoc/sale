##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLoyaltyDomainOperator(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env["loyalty.program"].create(
            {
                "name": "Test Program",
                "program_type": "promotion",
            }
        )
        cls.rule = cls.env["loyalty.rule"].create(
            {
                "program_id": cls.program.id,
            }
        )

    def test_sale_domain_equal_against_list_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.program.sale_domain = "[('partner_id.category_id', '=', [21])]"

    def test_sale_domain_not_equal_against_list_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.program.sale_domain = "[('partner_id.category_id', '!=', [21])]"

    def test_sale_domain_in_operator_is_allowed(self):
        self.program.sale_domain = "[('partner_id.category_id', 'in', [21])]"
        self.assertEqual(self.program.sale_domain, "[('partner_id.category_id', 'in', [21])]")

    def test_sale_domain_equal_against_scalar_is_allowed(self):
        self.program.sale_domain = "[('partner_id.category_id', '=', 21)]"
        self.assertEqual(self.program.sale_domain, "[('partner_id.category_id', '=', 21)]")

    def test_product_domain_equal_against_list_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.rule.product_domain = "[('categ_id', '=', [3])]"

    def test_product_domain_in_operator_is_allowed(self):
        self.rule.product_domain = "[('categ_id', 'in', [3])]"
        self.assertEqual(self.rule.product_domain, "[('categ_id', 'in', [3])]")

    def test_empty_domain_is_allowed(self):
        self.program.sale_domain = "[]"
        self.assertEqual(self.program.sale_domain, "[]")
