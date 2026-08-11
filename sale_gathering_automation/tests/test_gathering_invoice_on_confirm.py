##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestGatheringInvoiceOnConfirm(TransactionCase):
    """Si la cadena de ``action_confirm`` devuelve una acción en vez de ``True``,
    la factura de acopio se tiene que crear igual (ticket 124899)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.partner = cls.env["res.partner"].create({"name": "Cliente acopio"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto acopio",
                "type": "consu",
                "list_price": 100.0,
            }
        )
        cls.sale_type = cls.env["sale.order.type"].create(
            {
                "name": "Tipo acopio test",
                "picking_atomation": "validate_no_force",
                "invoicing_atomation": "create_invoice",
                "warehouse_id": cls.warehouse.id,
            }
        )
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].search([("model", "in", ("sale.order", "sale.order.line"))]).write(
                {"active": False}
            )

    def _create_gathering_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "type_id": self.sale_type.id,
                "warehouse_id": self.warehouse.id,
                "is_gathering": True,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 10.0,
                            "initial_qty_gathered": 10.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )

    def _confirm_returning(self, order, picking_automation_result):
        """Confirma la venta forzando lo que devuelve la automatización de entregas,
        que es lo que termina devolviendo la cadena de ``action_confirm``."""
        with patch.object(type(order), "run_picking_automation", return_value=picking_automation_result):
            return order.action_confirm()

    def test_gathering_invoiced_when_confirm_returns_an_action(self):
        # El caso del ticket: la cadena devuelve la acción de impresión de las
        # entregas validadas en vez de True.
        print_action = {"type": "ir.actions.client", "tag": "do_multi_print", "params": {"reports": []}}
        order = self._create_gathering_order()
        self._confirm_returning(order, print_action)
        self.assertEqual(order.state, "sale", "La venta no quedó confirmada: la automatización no corrió.")
        self.assertTrue(
            order.has_gathering_invoice,
            "La factura de anticipo del acopio se tiene que crear igual con una acción de por medio.",
        )

    def test_gathering_invoiced_when_confirm_returns_true(self):
        order = self._create_gathering_order()
        res = self._confirm_returning(order, True)
        self.assertIs(res, True)
        self.assertTrue(order.has_gathering_invoice)
