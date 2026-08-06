##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestPickingAutomationPrint(TransactionCase):
    """La automatización valida los pickings server-side: si descarta lo que
    devuelve ``button_validate`` no se imprime nada (ticket 124899)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.warehouse.delivery_steps = "ship_only"
        cls.partner = cls.env["res.partner"].create({"name": "Cliente automatización"})
        # Consumible: la validación no depende de que haya stock disponible.
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto automatización",
                "type": "consu",
            }
        )
        cls.sale_type = cls.env["sale.order.type"].create(
            {
                "name": "Tipo automatizado test",
                "picking_atomation": "validate_no_force",
                "invoicing_atomation": "none",
                "warehouse_id": cls.warehouse.id,
            }
        )
        # Con reglas de excepción activas action_confirm devuelve su asistente y la
        # automatización no llega a correr.
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].search([("model", "in", ("sale.order", "sale.order.line"))]).write(
                {"active": False}
            )

    def _confirm_automated_sale(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "type_id": self.sale_type.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1.0})],
            }
        )
        res = order.action_confirm()
        self.assertEqual(order.state, "sale", "La venta no quedó confirmada: la automatización no corrió.")
        self.assertEqual(order.picking_ids.state, "done", "La automatización debe validar la entrega.")
        return order, res

    def test_print_action_propagated(self):
        self.warehouse.out_type_id.auto_print_delivery_slip = True
        _order, res = self._confirm_automated_sale()
        self.assertIsInstance(res, dict, "action_confirm debe devolver la acción de impresión, no descartarla.")
        reports = res.get("params", {}).get("reports", [])
        self.assertIn("stock.report_deliveryslip", [report.get("report_name") for report in reports])

    def test_no_print_action_when_flag_is_off(self):
        # Sin imprimir al validar no hay nada que propagar: action_confirm tiene que
        # seguir devolviendo True como hasta ahora.
        self.warehouse.out_type_id.auto_print_delivery_slip = False
        _order, res = self._confirm_automated_sale()
        self.assertIs(res, True)
