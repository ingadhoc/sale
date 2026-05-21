# © 2026 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged("crm_sale_ux", "post_install", "-at_install")
class TestCrmSaleUxAutoSetWon(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.user.partner_id
        cls.product = cls.env["product.product"].create(
            {
                "name": "CRM Sale UX product",
                "type": "service",
                "list_price": 100.0,
            }
        )

    def _create_opportunity(self, name):
        stage = self.env["crm.stage"].search([("is_won", "=", False)], order="sequence, id", limit=1)
        return self.env["crm.lead"].create(
            {
                "name": name,
                "type": "opportunity",
                "partner_id": self.partner.id,
                "stage_id": stage.id,
                "user_id": self.env.user.id,
            }
        )

    def _create_quotation(self, opportunity):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "opportunity_id": opportunity.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": self.product.list_price,
                            "name": self.product.name,
                        }
                    )
                ],
            }
        )

    def test_confirm_quotation_does_not_set_won_when_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param("crm_sale_ux.auto_won_on_sale_confirm", False)
        opportunity = self._create_opportunity("Won setting disabled")
        stage_before = opportunity.stage_id

        quotation = self._create_quotation(opportunity)
        quotation.action_confirm()

        self.assertEqual(opportunity.stage_id, stage_before)
        self.assertFalse(opportunity.stage_id.is_won)

    def test_confirm_quotation_sets_won_when_enabled(self):
        self.env["ir.config_parameter"].sudo().set_param("crm_sale_ux.auto_won_on_sale_confirm", True)
        opportunity = self._create_opportunity("Won setting enabled")

        quotation = self._create_quotation(opportunity)

        sale_exception_installed = self.env["sale.order"]._fields.get("ignore_exception")
        if sale_exception_installed:
            self.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

        quotation.action_confirm()

        self.assertTrue(opportunity.stage_id.is_won)
        self.assertEqual(opportunity.probability, 100)
