##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import TransactionCase
from odoo.tools import float_is_zero


class SaleOrderTypeInvoicePolicyCommon(TransactionCase):
    """Datos del escenario y batería de invariantes de la política por tipo de venta.

    Los módulos que extienden la política heredan esta clase para correr las mismas
    invariantes sobre sus propios casos.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.precision = cls.env["decimal.precision"].precision_get("Product Unit")
        cls.partner = cls.env["res.partner"].create({"name": "Invoice Policy Customer", "customer_rank": 1})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        # la política del producto es "entregadas": así cada test muestra si mandó el tipo
        cls.product = cls.env["product.product"].create(
            {
                "name": "Invoice Policy Product",
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "delivery",
                "list_price": 100.0,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.warehouse.lot_stock_id, 100.0)
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    @classmethod
    def _sale_type(cls, invoice_policy, **values):
        return cls.env["sale.order.type"].create(
            dict({"name": "Type %s" % invoice_policy, "invoice_policy": invoice_policy}, **values)
        )

    def _order(self, sale_type, qty=10.0, product=None):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "type_id": sale_type.id,
                "order_line": [
                    (0, 0, {"product_id": (product or self.product).id, "product_uom_qty": qty, "price_unit": 100.0})
                ],
            }
        )
        order.action_confirm()
        return order

    def _deliver(self, picking, qty=None):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty if qty is None else qty
        picking.move_ids.picked = True
        picking.with_context(cancel_backorder=True)._action_done()

    # -- batería de invariantes -------------------------------------------------

    def assert_invariantes(self, order):
        """Propiedades que valen después de cualquier operación sobre la venta."""
        for line in order.order_line.filtered(lambda sol: not sol.display_type):
            pendiente = not float_is_zero(line.qty_to_invoice, precision_digits=self.precision)
            if order.state != "sale":
                self.assertFalse(
                    pendiente,
                    "una venta en %s no puede tener cantidad por facturar" % order.state,
                )
            elif pendiente:
                # el estado se deriva de qty_to_invoice: si el módulo escribe la cantidad
                # sin disparar el recálculo, acá se ve
                self.assertEqual(
                    line.invoice_status,
                    "to invoice",
                    "qty_to_invoice %s con invoice_status %s" % (line.qty_to_invoice, line.invoice_status),
                )
