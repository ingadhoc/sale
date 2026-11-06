from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectWithoutCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrConfig = cls.env["ir.config_parameter"].sudo()
        cls.partner = cls.env["res.partner"].create({"name": "Project customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Service with project",
                "type": "service",
                "service_tracking": "project_only",
                "project_id": False,
            }
        )

    def _confirm_order(self, project=None):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "project_id": project.id if project else False,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )
        order.action_confirm()
        return order

    def test_project_company_follows_setting(self):
        """The project created when confirming a sale, and its analytic account,
        have no company only when sale_ux.analytic_account_without_company is set."""
        AnalyticAccount = self.env["account.analytic.account"]
        for setting, expected_company in ((True, self.env["res.company"]), (False, self.env.company)):
            with self.subTest(analytic_account_without_company=setting):
                # Set the sale_ux setting under test
                self.IrConfig.set_bool("sale_ux.analytic_account_without_company", setting)
                accounts_before = AnalyticAccount.search([])
                # Confirm an order whose line generates a project
                order = self._confirm_order()
                line = order.order_line
                project = line.project_id
                # One project, created for this line and linked to it
                self.assertEqual(order.state, "sale")
                self.assertEqual(len(project), 1, "Confirming the order must create one project")
                self.assertEqual(project.sale_line_id, line)
                # The order creates one analytic account, and the project uses it
                new_accounts = AnalyticAccount.search([]) - accounts_before
                self.assertEqual(new_accounts, project.account_id, "No analytic account may be left unused")
                # The company of both depends only on the setting
                self.assertEqual(project.company_id, expected_company)
                self.assertEqual(project.account_id.company_id, expected_company)

    def test_order_with_project_of_a_company(self):
        """With the setting set, an order whose project has an analytic account
        with company is confirmed, and the new project gets its own account."""
        self.IrConfig.set_bool("sale_ux.analytic_account_without_company", True)
        plan, _other_plans = self.env["account.analytic.plan"]._get_all_plans()
        account = self.env["account.analytic.account"].create(
            {"name": "Existing project account", "plan_id": plan.id, "company_id": self.env.company.id}
        )
        existing = self.env["project.project"].create(
            {"name": "Existing project", "allow_billable": True, "account_id": account.id}
        )
        accounts_before = self.env["account.analytic.account"].search([])
        # Confirm an order that points to the existing project
        order = self._confirm_order(project=existing)
        project = order.order_line.project_id
        self.assertEqual(order.state, "sale")
        self.assertEqual(len(project), 1, "Confirming the order must create one project")
        # The new project has no company, and neither has its own account
        self.assertFalse(project.company_id)
        self.assertTrue(project.account_id)
        self.assertNotEqual(project.account_id, account)
        self.assertFalse(project.account_id.company_id)
        new_accounts = self.env["account.analytic.account"].search([]) - accounts_before
        self.assertEqual(new_accounts, project.account_id, "No analytic account may be left unused")
        # The existing project and its account keep their company
        self.assertEqual(existing.company_id, self.env.company)
        self.assertEqual(account.company_id, self.env.company)
