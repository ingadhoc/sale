from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestDeliveryChainReceipt(AccountTestInvoicingCommon):
    """A receipt is never a leg of the delivery chain (ticket 131106).

    With buy-to-order the receipt of the purchase inherits the sale's
    procurement group, so ``picking.sale_id`` points at the order and the
    prepaid block reaches it: the customer has to pay before the warehouse
    can take the goods in from the supplier.

    The rule graph cannot tell the two apart on its own, because it is
    reachability and not direction: from the stock a receipt lands in, the
    warehouse's own outgoing rules are always reachable.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.delivery_steps = "ship_only"
        cls.partner = cls.env["res.partner"].create({"name": "Cliente prepago", "customer_rank": 1})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Almacenable bajo pedido",
                "type": "consu",
                "is_storable": True,
                "list_price": 100.0,
            }
        )
        cls.order_type = cls.env["sale.order.type"].create(
            {"name": "Prepago bloquea entrega", "invoice_policy": "prepaid_block_delivery"}
        )
        # Active exception rules keep the order in draft on confirmation, so
        # no picking is created and the sale never reaches its procurement group.
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].sudo().search([("active", "=", True)]).write({"active": False})
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "type_id": cls.order_type.id,
                "order_line": [(0, 0, {"product_id": cls.product.id, "product_uom_qty": 5})],
            }
        )
        cls.order.action_confirm()
        cls.delivery = cls.order.picking_ids
        assert cls.delivery, "the order was confirmed without creating any picking"
        # The receipt of a purchase raised by this sale: same procurement
        # group, which is what makes Odoo show it among the sale's transfers.
        cls.receipt = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.warehouse.in_type_id.id,
                "move_type": "direct",
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": cls.warehouse.lot_stock_id.id,
                # The group goes on the move: picking.group_id is related to
                # it, so setting it on the picking alone is dropped on create.
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": cls.product.name,
                            "product_id": cls.product.id,
                            "product_uom_qty": 5,
                            "group_id": cls.order.procurement_group_id.id,
                            "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                            "location_dest_id": cls.warehouse.lot_stock_id.id,
                        },
                    )
                ],
            }
        )

    def test_receipt_is_not_delivery_chain(self):
        self.assertEqual(self.receipt.sale_id, self.order, "el escenario necesita la recepción ligada a la venta")
        self.assertFalse(self.receipt._is_delivery_chain())

    def test_delivery_is_delivery_chain(self):
        self.assertTrue(self.delivery._is_delivery_chain())

    def test_receipt_validates_with_the_sale_unpaid(self):
        self.assertFalse(self.receipt._check_sale_paid(), "la venta tiene que estar impaga")
        self.receipt.action_confirm()
        for move in self.receipt.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        self.receipt.button_validate()
        self.assertEqual(self.receipt.state, "done")
