# © 2026 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestCreditWithConfirmedOrders(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root_company = cls.env.company
        cls.branch = cls.env["res.company"].create({"name": "Branch", "parent_id": cls.root_company.id})
        cls.env.user.company_ids |= cls.branch
        cls.env.user.write({"group_ids": [Command.link(cls.env.ref("sale_exception_credit_limit.credit_config").id)]})
        cls.root_company.account_use_credit_limit = True
        cls.partner = cls.partner_a
        # A credit limit different from the company one enables use_partner_credit_limit
        cls.partner.credit_limit = 5000.0
        # Only one unpaid invoice, no sale orders and no draft invoices
        cls.invoice = cls.init_invoice("out_invoice", partner=cls.partner, amounts=[1000.0], post=True)
        cls.expected = cls.invoice.amount_residual

    def _credit_taken(self, company):
        partner = self.partner.with_company(company).with_context(
            allowed_company_ids=[self.root_company.id, self.branch.id]
        )
        return partner.credit_with_confirmed_orders

    def test_credit_taken_is_not_multiplied_by_hierarchy_companies(self):
        """The balance of the hierarchy must be counted once, not once per company"""
        self.assertTrue(self.expected)
        self.assertEqual(self.partner.with_company(self.root_company).credit, self.expected)
        self.assertEqual(self._credit_taken(self.root_company), self.expected)

    def test_credit_taken_is_the_same_from_any_company_of_the_hierarchy(self):
        self.assertEqual(self._credit_taken(self.branch), self.expected)
