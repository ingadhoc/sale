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
        """The project created when confirming a sale has no company only when
        sale_ux.analytic_account_without_company is set."""
        for setting, expected_company in ((True, self.env["res.company"]), (False, self.env.company)):
            with self.subTest(analytic_account_without_company=setting):
                # Set the sale_ux setting under test
                self.IrConfig.set_bool("sale_ux.analytic_account_without_company", setting)
                # Confirm an order whose line generates a project
                order = self._confirm_order()
                line = order.order_line
                # One project, created for this line and linked to it
                self.assertEqual(order.state, "sale")
                self.assertEqual(len(line.project_id), 1, "Confirming the order must create one project")
                self.assertEqual(line.project_id.sale_line_id, line)
                # Its company depends only on the setting
                self.assertEqual(line.project_id.company_id, expected_company)
