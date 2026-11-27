##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleOrderTypeInvoiceCompany(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_journal = cls.company_data["default_journal_sale"]
        cls.other_company_data = cls.setup_other_company()
        cls.other_sale_journal = cls.other_company_data["default_journal_sale"]

    def test_01_type_without_company_takes_the_journal_company(self):
        sale_type = self.env["sale.order.type"].create(
            {"name": "Type without company", "company_id": False, "journal_id": self.sale_journal.id}
        )
        self.assertEqual(sale_type.invoice_company_id, self.sale_journal.company_id)

    def test_02_clearing_the_company_keeps_the_journal(self):
        sale_type = self.env["sale.order.type"].create(
            {"name": "Type with company", "company_id": self.env.company.id, "journal_id": self.sale_journal.id}
        )
        self.assertEqual(sale_type.invoice_company_id, self.env.company)
        sale_type.company_id = False
        self.assertEqual(sale_type.invoice_company_id, self.sale_journal.company_id)

    def test_03_journal_of_another_company_is_not_allowed(self):
        with self.assertRaises(ValidationError):
            self.env["sale.order.type"].create(
                {
                    "name": "Type with a foreign journal",
                    "company_id": self.env.company.id,
                    "journal_id": self.other_sale_journal.id,
                }
            )

    def test_04_without_invoice_company_any_sale_journal_is_allowed(self):
        sale_type = self.env["sale.order.type"].create({"name": "Type without journal", "company_id": False})
        self.assertFalse(sale_type.invoice_company_id)
        sale_type.journal_id = self.other_sale_journal
        self.assertEqual(sale_type.journal_id, self.other_sale_journal)
