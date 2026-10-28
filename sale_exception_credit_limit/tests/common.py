##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import TransactionCase


class CreditLimitCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.company.account_use_credit_limit = True
        cls.pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Credit Limit Pricelist",
                "currency_id": cls.company.currency_id.id,
                "company_id": False,
            }
        )
        # invoice_policy delivery keeps the native credit_to_invoice at zero while
        # nothing is delivered: that is what separates this module's figure from it
        cls.product = cls.env["product.product"].create(
            {
                "name": "Credit Limit Product",
                "type": "consu",
                "invoice_policy": "delivery",
                "list_price": 100.0,
                "taxes_id": [Command.clear()],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Credit Limit Customer"})
        cls.tracked_partners = cls.partner
        cls.tracked_orders = cls.env["sale.order"]

    @classmethod
    def _create_order(cls, amount, partner=None, company=None):
        order = (
            cls.env["sale.order"]
            .with_company(company or cls.company)
            .create(
                {
                    "partner_id": (partner or cls.partner).id,
                    "pricelist_id": cls.pricelist.id,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": cls.product.id,
                                "product_uom_qty": 1,
                                "price_unit": amount,
                                "tax_ids": [Command.clear()],
                            }
                        )
                    ],
                }
            )
        )
        cls.tracked_orders |= order
        return order

    def assert_invariants(self):
        """Propiedades que valen después de cualquier operación del módulo."""
        for partner in self.tracked_partners:
            if not partner.use_partner_credit_limit:
                self.assertEqual(
                    partner.credit_with_confirmed_orders,
                    0.0,
                    "sin límite por cliente el crédito tomado tiene que ser cero",
                )
        for order in self.tracked_orders:
            if order.state in ("draft", "sent"):
                self.assertEqual(
                    order.check_credit_limit_ok(),
                    not order.partner_credit_warning,
                    "el chequeo de la regla y el aviso de crédito tienen que decir lo mismo",
                )
