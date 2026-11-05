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

    def _confirm_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
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
