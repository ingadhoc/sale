##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests import new_test_user, tagged

from .common import CreditLimitCommon


@tagged("post_install", "-at_install")
class TestCreditConfigRights(CreditLimitCommon):
    """Cubre: el candado de escritura sobre los parámetros de crédito (5), la
    salida para una filial que copia al padre (6) y el flag de la vista."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoicing_user = new_test_user(
            cls.env,
            login="credit_limit_invoicing",
            groups="base.group_user,base.group_partner_manager,account.group_account_invoice",
        )
        cls.config_user = new_test_user(
            cls.env,
            login="credit_limit_config",
            groups="base.group_user,base.group_partner_manager,"
            "account.group_account_invoice,"
            "sale_exception_credit_limit.credit_config",
        )

    def test_user_credit_config_reflects_the_group(self):
        self.assertFalse(self.partner.with_user(self.invoicing_user).user_credit_config)
        self.assertTrue(self.partner.with_user(self.config_user).user_credit_config)

    def test_write_without_rights_is_rejected(self):
        for field, value in [("credit_limit", 500.0), ("use_partner_credit_limit", True)]:
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    self.partner.with_user(self.invoicing_user).write({field: value})

    def test_write_with_rights_goes_through(self):
        self.partner.with_user(self.config_user).write({"credit_limit": 500.0})
        self.assertEqual(self.partner.credit_limit, 500.0)
        self.assert_invariants()

    def test_child_copying_the_parent_limit_needs_no_rights(self):
        self.partner.write({"credit_limit": 700.0, "use_partner_credit_limit": True})
        child = self.env["res.partner"].create({"name": "Credit Limit Branch", "parent_id": self.partner.id})
        child.with_user(self.invoicing_user).write({"credit_limit": 700.0})
        self.assertEqual(child.credit_limit, 700.0)
        with self.assertRaises(ValidationError):
            child.with_user(self.invoicing_user).write({"credit_limit": 800.0})
