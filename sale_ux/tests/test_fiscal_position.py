from odoo.tests.common import TransactionCase


class TestSaleOrderFiscalPosition(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.delivery_group = cls.env.ref("account.group_delivery_invoice_address")
        cls.fiscal_position = cls.env["account.fiscal.position"].create({"name": "Test FP"})
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "property_account_position_id": cls.fiscal_position.id,
            }
        )

    def setUp(self):
        super().setUp()
        # Ensure user doesn't have the delivery group so our override is executed
        self.env.user.write({"group_ids": [(3, self.delivery_group.id)]})

    def test_fiscal_position_computed_from_partner(self):
        """Without group_delivery_invoice_address, fiscal position is set from partner."""
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.assertEqual(order.fiscal_position_id, self.fiscal_position)

    def test_fiscal_position_false_without_partner(self):
        """Fiscal position is cleared when no partner is set on the order."""
        order = self.env["sale.order"].new(
            {"partner_id": self.partner.id, "fiscal_position_id": self.fiscal_position.id}
        )
        order.partner_id = False
        order._compute_fiscal_position_id()
        self.assertFalse(order.fiscal_position_id)

    def test_fiscal_position_fallback_to_super_with_group(self):
        """With group_delivery_invoice_address, the standard Odoo compute is used."""
        self.env.user.write({"group_ids": [(4, self.delivery_group.id)]})
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        # super() also resolves to partner's property_account_position_id in this case
        self.assertEqual(order.fiscal_position_id, self.fiscal_position)
