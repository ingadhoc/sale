##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.base_exception.exceptions import BaseExceptionError
from odoo.tests import tagged

from .common import CreditLimitCommon


@tagged("post_install", "-at_install")
class TestCreditTaken(CreditLimitCommon):
    def test_credit_taken_blocks_confirmation(self):
        """Cubre: el crédito tomado (1), el límite apagado (2), el aviso que
        agrega el módulo sobre el nativo (3) y el bloqueo de la confirmación (4).
        """
        with self.subTest("sin límite por cliente el crédito tomado es cero"):
            self.assertFalse(self.partner.use_partner_credit_limit)
            self.assertEqual(self.partner.credit_with_confirmed_orders, 0.0)
            self.assert_invariants()

        self.partner.write({"credit_limit": 1000.0, "use_partner_credit_limit": True})

        with self.subTest("una orden confirmada sin facturar suma al crédito tomado"):
            first_order = self._create_order(500.0)
            first_order.action_confirm()
            self.assertEqual(first_order.state, "sale")
            self.partner.invalidate_recordset(["credit_with_confirmed_orders"])
            self.assertEqual(self.partner.credit_with_confirmed_orders, 500.0)

        with self.subTest("el aviso aparece aunque el crédito nativo no lo dispare"):
            second_order = self._create_order(600.0)
            # nada entregado todavía: la cuenta nativa no ve la orden confirmada
            self.assertEqual(self.partner.credit, 0.0)
            self.assertEqual(self.partner.credit_to_invoice, 0.0)
            self.assertTrue(second_order.partner_credit_warning)
            self.assertIn("1,100", second_order.partner_credit_warning.replace(".", ","))

        with self.subTest("con aviso la orden no se confirma"):
            self.assertFalse(second_order.check_credit_limit_ok())
            with self.assertRaises(BaseExceptionError):
                second_order.action_confirm()
            self.assertEqual(second_order.state, "draft")
            self.assert_invariants()

        with self.subTest("cerrar la facturación del pedido libera el crédito"):
            # invoicing_closed es nuevo en 20 y el crédito nativo lo excluye
            first_order.action_close_invoicing()
            self.partner.invalidate_recordset(["credit_with_confirmed_orders"])
            self.assertEqual(self.partner.credit_with_confirmed_orders, 0.0)
            second_order.invalidate_recordset(["partner_credit_warning"])
            self.assertFalse(second_order.partner_credit_warning)
            self.assert_invariants()
            first_order.action_reopen_order()
            self.partner.invalidate_recordset(["credit_with_confirmed_orders"])
            self.assertEqual(self.partner.credit_with_confirmed_orders, 500.0)
            second_order.invalidate_recordset(["partner_credit_warning"])

        with self.subTest("ignorando la excepción la misma orden sí se confirma"):
            # prueba que lo que frenó la confirmación fue la regla del módulo
            second_order.ignore_exception = True
            second_order.action_confirm()
            self.assertEqual(second_order.state, "sale")
