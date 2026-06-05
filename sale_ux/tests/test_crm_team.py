from odoo.tests import new_test_user, tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestCrmTeam(SaleUxCommon):
    def test_member_domain_restricts_users_by_default(self):
        domain = self.env["crm.team"]._domain_member_ids()

        self.assertIn("share", domain)

    def test_member_domain_allows_any_salesman_for_group(self):
        user = new_test_user(
            self.env,
            login="sale_ux_any_salesman_user",
            groups="sale_ux.group_allow_any_user_as_salesman",
        )

        domain = self.env["crm.team"].with_user(user)._domain_member_ids()

        self.assertEqual(domain, [])
