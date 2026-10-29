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
        cls.other_root = cls.setup_other_company()["company"]
        cls.env.user.company_ids |= cls.branch
        cls.env.user.write({"groups_id": [Command.link(cls.env.ref("sale_exception_credit_limit.credit_config").id)]})
        cls.partner = cls.partner_a
        # The credit limit is company dependent: set it for every company so the check also runs from the branch.
        # A credit limit different from the company one enables use_partner_credit_limit
        for company in cls.root_company | cls.branch | cls.other_root:
            company.account_use_credit_limit = True
            cls.partner.with_company(company).credit_limit = 5000.0
        # Only one unpaid invoice, no sale orders and no draft invoices
        cls.invoice = cls.init_invoice("out_invoice", partner=cls.partner, amounts=[1000.0], post=True)
        cls.expected = cls.invoice.amount_residual

    def _credit_taken(self, company):
        # with_company goes last: with_context(allowed_company_ids=...) would override it and the computation would
        # always run from the first allowed company
        partner = self.partner.with_context(
            allowed_company_ids=[self.root_company.id, self.branch.id, self.other_root.id]
        ).with_company(company)
        return partner.credit_with_confirmed_orders

    def test_credit_taken_is_not_multiplied_by_hierarchy_companies(self):
        """The balance of the hierarchy must be counted once, not once per company"""
        self.assertTrue(self.expected)
        self.assertEqual(self.partner.with_company(self.root_company).credit, self.expected)
        self.assertEqual(self._credit_taken(self.root_company), self.expected)

    def test_credit_taken_is_the_same_from_any_company_of_the_hierarchy(self):
        self.assertEqual(self._credit_taken(self.branch), self.expected)

    def test_credit_taken_adds_each_root_company_once(self):
        """The balance of other companies tree is still added, but once for each root company"""
        other_invoice = self.init_invoice(
            "out_invoice", partner=self.partner, amounts=[500.0], post=True, company=self.other_root
        )
        other_amount = self.other_root.currency_id._convert(
            other_invoice.amount_residual, self.root_company.currency_id, self.root_company, other_invoice.date
        )
        expected = self.expected + other_amount
        self.assertEqual(self._credit_taken(self.root_company), expected)
        self.assertEqual(self._credit_taken(self.branch), expected)

    def test_credit_taken_does_not_depend_on_the_companies_checked_by_the_user(self):
        """A user without administration rights must see the same credit taken whatever companies he has checked"""
        other_invoice = self.init_invoice(
            "out_invoice", partner=self.partner, amounts=[500.0], post=True, company=self.other_root
        )
        other_amount = self.other_root.currency_id._convert(
            other_invoice.amount_residual, self.root_company.currency_id, self.root_company, other_invoice.date
        )
        all_companies = self.root_company | self.branch | self.other_root
        seller = self.env["res.users"].create(
            {
                "name": "Seller",
                "login": "seller_credit_taken",
                "company_id": self.root_company.id,
                "company_ids": [Command.set(all_companies.ids)],
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("sales_team.group_sale_salesman").id,
                            self.env.ref("account.group_account_invoice").id,
                        ]
                    )
                ],
            }
        )
        self.assertFalse(seller.has_group("base.group_erp_manager"))
        partner = self.partner.with_user(seller)
        # with_company goes last, see _credit_taken
        all_checked = partner.with_context(allowed_company_ids=all_companies.ids).with_company(self.root_company)
        one_checked = partner.with_context(allowed_company_ids=self.root_company.ids).with_company(self.root_company)
        expected = self.expected + other_amount
        self.assertEqual(all_checked.credit_with_confirmed_orders, expected)
        # The computed value is cached by company only, so clear it to really compute it again with the other context
        self.env.invalidate_all()
        self.assertEqual(one_checked.credit_with_confirmed_orders, expected)
