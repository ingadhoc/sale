##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.sale_exception_credit_limit import _post_init_credit
from odoo.tests import tagged

from .common import CreditLimitCommon


@tagged("post_install", "-at_install")
class TestCompanyHierarchy(CreditLimitCommon):
    """Cubre: la herencia del flag en el árbol de compañías y el crédito sumado
    sobre toda la jerarquía (7), y el hook de instalación (8)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_company = cls.env["res.company"].create(
            {"name": "Credit Limit Parent", "currency_id": cls.company.currency_id.id}
        )
        cls.child_company = cls.env["res.company"].create(
            {
                "name": "Credit Limit Child",
                "parent_id": cls.parent_company.id,
                "currency_id": cls.company.currency_id.id,
            }
        )
        cls.env.user.company_ids = [
            Command.link(cls.parent_company.id),
            Command.link(cls.child_company.id),
        ]
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                allowed_company_ids=cls.env.user.company_ids.ids,
            )
        )

    def test_child_company_follows_the_parent_flag(self):
        self.parent_company.account_use_credit_limit = True
        self.assertTrue(self.child_company.account_use_credit_limit)
        self.parent_company.account_use_credit_limit = False
        self.assertFalse(self.child_company.account_use_credit_limit)

    def test_hierarchy_covers_the_whole_tree(self):
        hierarchy = self.env["res.partner"]._get_company_hierarchy(self.child_company)
        self.assertEqual(hierarchy, self.parent_company | self.child_company)
        self.assertEqual(
            self.env["res.partner"]._get_company_hierarchy(self.parent_company),
            hierarchy,
            "desde el padre o desde la hija, el árbol es el mismo",
        )

    def test_credit_taken_adds_up_the_sister_companies(self):
        self.parent_company.account_use_credit_limit = True
        partner = self.env["res.partner"].create({"name": "Credit Limit Group Customer"})
        partner.with_company(self.parent_company).write({"credit_limit": 1000.0, "use_partner_credit_limit": True})
        order = self._create_order(300.0, partner=partner, company=self.child_company)
        order.with_company(self.child_company).action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(
            partner.with_company(self.parent_company).credit_with_confirmed_orders,
            300.0,
            "una orden de la hija tiene que contar en el crédito del padre",
        )

    def test_post_init_hook_turns_the_limit_on(self):
        self.parent_company.account_use_credit_limit = False
        self.assertFalse(self.child_company.account_use_credit_limit)
        _post_init_credit(self.env)
        self.assertTrue(self.parent_company.account_use_credit_limit)
        self.assertTrue(self.child_company.account_use_credit_limit)
