from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestReturnOfReturn(AccountTestInvoicingCommon):
    """Returned quantity is net of the returns of refunded returns sent back to the customer."""

    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref("sales_team.group_sale_manager")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.delivery_steps = "ship_only"
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner", "customer_rank": 1})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test storable",
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "order",
                "list_price": 100.0,
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
                "property_account_expense_id": cls.company_data["default_account_expense"].id,
            }
        )
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].sudo().search([("active", "=", True)]).write({"active": False})

    def setUp(self):
        super().setUp()
        self.order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 10.0, "price_unit": 100.0})],
            }
        )
        self.order.action_confirm()
        self.line = self.order.order_line
        self.delivery = self.order.picking_ids
        self._validate(self.delivery)

    def _validate(self, picking):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.move_line_ids.unlink()
            move.quantity = move.product_uom_qty
            move.picked = True
        picking._action_done()

    def _return(self, picking, quantity=10.0, to_refund=True):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_ids=picking.ids, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.to_refund = to_refund
            line.quantity = quantity
        action = wizard.action_create_returns()
        returned = self.env["stock.picking"].browse(action["res_id"])
        self._validate(returned)
        return returned

    def _assert_line(self, delivered, returned, to_invoice):
        self.assertEqual(self.line.qty_delivered, delivered)
        self.assertEqual(self.line.quantity_returned, returned)
        self.assertEqual(self.line.qty_to_invoice, to_invoice)

    def test_partial_return_of_redelivery(self):
        """Delivery, return, redelivery, then a partial return of the redelivery."""
        first_return = self._return(self.delivery)
        redelivery = self._return(first_return)
        self._return(redelivery, quantity=4.0)

        self._assert_line(delivered=6.0, returned=4.0, to_invoice=6.0)

    def test_crossed_returns_and_redeliveries(self):
        """Two returns of the same delivery and three redeliveries of the same return."""
        first_return = self._return(self.delivery)
        self._return(first_return)
        second_redelivery = self._return(first_return)
        self._return(first_return)
        self._return(second_redelivery)
        self._return(self.delivery)

        self._assert_line(delivered=10.0, returned=0.0, to_invoice=10.0)

    def test_redelivering_more_than_returned_is_not_negative(self):
        """Redelivering more than was returned is an over-delivery, not a negative return."""
        first_return = self._return(self.delivery)
        self._return(first_return)
        self._return(first_return)

        self._assert_line(delivered=20.0, returned=0.0, to_invoice=10.0)

    def test_redelivery_of_non_refunded_return_is_ignored(self):
        """A return that was not refunded is not counted, so neither is its redelivery."""
        first_return = self._return(self.delivery, to_refund=False)
        self._return(first_return)

        self.assertEqual(self.line.quantity_returned, 0.0)
        self.assertEqual(self.line.qty_to_invoice, 10.0)
