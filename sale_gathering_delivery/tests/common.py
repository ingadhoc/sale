from odoo import Command
from odoo.addons.sale_gathering.tests.common import SaleGatheringCommon


class SaleGatheringDeliveryCommon(SaleGatheringCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.delivery_product = cls.env["product.product"].create(
            {
                "name": "Sale Gathering Delivery Freight",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 50.0,
                "property_account_income_id": cls.income_account.id,
                "property_account_expense_id": cls.expense_account.id,
                "taxes_id": [Command.clear()],
                "supplier_taxes_id": [Command.clear()],
            }
        )
        cls.carrier = cls.env["delivery.carrier"].create(
            {
                "name": "Sale Gathering Delivery Carrier",
                "delivery_type": "fixed",
                "fixed_price": 50.0,
                "product_id": cls.delivery_product.id,
                "company_id": cls.env.company.id,
            }
        )

    def _add_delivery_line(self, order, *, price=50.0):
        """Add the carrier line the way the Shipping button does."""
        wizard = self.env["choose.delivery.carrier"].create(
            {"order_id": order.id, "carrier_id": self.carrier.id, "delivery_price": price}
        )
        wizard.button_confirm()
        return order.order_line.filtered("is_delivery")
