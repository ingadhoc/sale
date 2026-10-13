##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestPrepareForAutomaticInvoicing(TransactionCase):
    """El hook previo a facturar sólo alcanza a los traslados que se facturan acá."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.warehouse.delivery_steps = "ship_only"
        cls.partner = cls.env["res.partner"].create({"name": "Cliente hook test"})
        # Consumible: la validación no depende de que haya stock disponible.
        cls.product = cls.env["product.product"].create({"name": "Producto hook test", "type": "consu"})
        cls.sale_type = cls.env["sale.order.type"].create(
            {
                "name": "Tipo hook test",
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
        order.action_confirm()
        self.assertEqual(order.picking_ids.state, "done", "La automatización debe validar la entrega.")
        return order

    def test_hook_skips_the_picking_when_the_type_does_not_invoice(self):
        """Un tipo que no factura al validar no tiene nada que preparar."""
        picking_model = type(self.env["stock.picking"])
        with patch.object(picking_model, "_prepare_for_automatic_invoicing", autospec=True) as hook:
            self._confirm_automated_sale()
        self.assertTrue(hook.called, "El hook se llama siempre, aunque sea sobre un conjunto vacío.")
        for call in hook.call_args_list:
            self.assertFalse(call.args[0], "Sin facturación automática el hook no toca ningún traslado.")

    def test_only_the_orders_being_invoiced_are_selected(self):
        order = self._confirm_automated_sale()
        self.assertFalse(
            order._orders_to_invoice_automatically(),
            "Con la automatización en None el pedido no entra.",
        )
        self.sale_type.invoicing_atomation = "create_invoice"
        self.assertEqual(order._orders_to_invoice_automatically(), order)
