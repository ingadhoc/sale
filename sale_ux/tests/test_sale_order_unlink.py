##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleOrderUnlink(TestSaleCommon):
    @classmethod
    def setup_independent_user(cls):
        return None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "SO Unlink Test Service",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 100.0,
            }
        )

    def _create_sale_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )

    def _create_linked_invoice(self, sale_order):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": sale_order.partner_id.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "SO unlink traceability test",
                            "product_id": self.product.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "sale_line_ids": [(6, 0, sale_order.order_line.ids)],
                        },
                    )
                ],
            }
        )

    def test_unlink_blocked_if_has_invoices(self):
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        self._create_linked_invoice(sale_order)
        sale_order.action_cancel()

        with self.assertRaisesRegex(
            UserError,
            "You cannot delete this sales order because it has related invoices",
        ):
            sale_order.unlink()

    def test_unlink_allowed_if_no_invoices(self):
        sale_order = self._create_sale_order()
        sale_order.action_cancel()
        sale_order.unlink()

        self.assertFalse(sale_order.exists())
