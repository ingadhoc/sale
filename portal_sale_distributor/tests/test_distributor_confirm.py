##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests.common import TransactionCase


class TestDistributorConfirm(TransactionCase):
    """`action_confirm_distributor` frente al base_exception nuevo, que guarda las
    excepciones en su propia transacción y levanta `BaseExceptionError` en vez de
    devolverlas. El distribuidor tiene que seguir recibiendo el mensaje en el chatter."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # solo deciden las reglas de este test, no las que traiga la base
        cls.env["exception.rule"].search([]).write({"active": False})
        cls.partner = cls.env["res.partner"].create({"name": "Distributor confirm test"})
        cls.product = cls.env["product.product"].create({"name": "Distributor confirm product", "type": "consu"})
        cls.rule = cls.env["exception.rule"].create(
            {
                "name": "Blocks the distributor",
                "model": "sale.order",
                "exception_type": "by_py_code",
                "code": "failed = self.client_order_ref == 'block'",
                "sequence": 10,
            }
        )

    def _new_order(self, client_order_ref):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "client_order_ref": client_order_ref,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )

    def _blocked_messages(self, order):
        return order.message_ids.filtered(lambda m: "contiene excepciones" in (m.body or ""))

    def test_order_with_exception_is_not_confirmed(self):
        order = self._new_order("block")
        order.action_confirm_distributor()
        self.assertEqual(order.state, "draft")
        self.assertTrue(self._blocked_messages(order))

    def test_order_without_exception_is_confirmed(self):
        order = self._new_order("free")
        order.action_confirm_distributor()
        self.assertEqual(order.state, "sale")
        self.assertFalse(self._blocked_messages(order))
