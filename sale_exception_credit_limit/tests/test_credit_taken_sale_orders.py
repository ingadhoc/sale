# © 2026 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestCreditTakenSaleOrders(AccountTestInvoicingCommon):
    """Qué suma al Crédito Tomado desde las órdenes de venta (tarea 75860)."""

    @classmethod
    def get_default_groups(cls):
        # El usuario de AccountTestInvoicingCommon no trae grupos de ventas y no
        # puede crear la orden del escenario.
        return super().get_default_groups() | cls.quick_ref("sales_team.group_sale_manager")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.account_use_credit_limit = True
        cls.env.user.write({"group_ids": [Command.link(cls.env.ref("sale_exception_credit_limit.credit_config").id)]})
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Credit Taken Partner",
                "customer_rank": 1,
                "use_partner_credit_limit": True,
                "credit_limit": 100000.0,
            }
        )
        product_vals = {
            "name": "Credit Taken Product",
            "type": "consu",
            "invoice_policy": "order",
            "list_price": 100.0,
            "property_account_income_id": cls.company_data["default_account_revenue"].id,
            "property_account_expense_id": cls.company_data["default_account_expense"].id,
        }
        # is_storable is defined by stock, which this module does not depend on.
        if "is_storable" in cls.env["product.product"]._fields:
            product_vals["is_storable"] = True
        cls.product = cls.env["product.product"].create(product_vals)
        # Evitar que reglas de excepción bloqueen la confirmación en runbot.
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].sudo().search([("active", "=", True)]).write({"active": False})

    def _credit_taken(self):
        self.partner.invalidate_recordset(["credit_with_confirmed_orders"])
        return self.partner.credit_with_confirmed_orders

    def _create_order(self, qty, warehouse=None):
        vals = {
            "partner_id": self.partner.id,
            "order_line": [
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": qty,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ],
        }
        if warehouse:
            vals["warehouse_id"] = warehouse.id
        order = self.env["sale.order"].create(vals)
        order.action_confirm()
        if order.state not in ("sale", "done"):
            self.skipTest("Order could not be confirmed in current module stack")
        return order

    def _validate(self, picking):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.move_line_ids.unlink()
            move.quantity = move.product_uom_qty
            move.picked = True
        picking._action_done()

    def _make_return(self, picking, quantity):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_ids=picking.ids, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.to_refund = True
            line.quantity = quantity
        returned = self.env["stock.picking"].browse(wizard.action_create_returns()["res_id"])
        self._validate(returned)
        return returned

    def test_forced_invoiced_status_stops_taking_credit(self):
        """Una OV cerrada con "Nada que facturar" forzado deja de consumir crédito."""
        if not self.env["sale.order"]._fields.get("force_invoiced_status"):
            self.skipTest("sale_ux is not installed")
        order = self._create_order(2.0)

        self.assertEqual(self._credit_taken(), 200.0)

        order.sudo().force_invoiced_status = "no"

        self.assertEqual(self._credit_taken(), 0.0)

    def test_invoiced_and_returned_line_leaves_nothing_pending(self):
        """Una línea facturada y después devuelta no deja pendiente negativo."""
        if not self.env["sale.order.line"]._fields.get("quantity_returned"):
            self.skipTest("sale_stock_ux is not installed")
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        warehouse.delivery_steps = "ship_only"
        order = self._create_order(2.0, warehouse=warehouse)
        self._validate(order.picking_ids)
        order._create_invoices(final=True).action_post()
        self.assertEqual(order.order_line.qty_invoiced, 2.0)

        self._make_return(order.picking_ids[0], 2.0)

        self.assertEqual(order.order_line.quantity_returned, 2.0)
        # La factura emitida sigue adeudada: el Crédito Tomado es esa deuda y nada más.
        # Antes del fix la línea devolvía -2 pendientes y restaba 200 de la deuda real.
        self.assertEqual(self._credit_taken(), self.partner.credit)
        self.assertEqual(self._credit_taken(), 200.0)

    def test_negative_line_return_does_not_duplicate_pending(self):
        """Una línea negativa devuelta no deja más pendiente del que tenía."""
        if not self.env["sale.order.line"]._fields.get("quantity_returned"):
            self.skipTest("sale_stock_ux is not installed")
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        order = self._create_order(-4.0, warehouse=warehouse)
        line = order.order_line
        # El movimiento de devolución se crea a mano: una línea negativa no dispara reglas de stock.
        # sudo porque el usuario de AccountTestInvoicingCommon no está en los grupos de stock.
        self.env["stock.move"].sudo().create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 4.0,
                "quantity": 4.0,
                "picked": True,
                "location_id": self.env.ref("stock.stock_location_customers").id,
                "location_dest_id": warehouse.lot_stock_id.id,
                "company_id": self.env.company.id,
                "sale_line_id": line.id,
                "to_refund": True,
            }
        )._action_done()

        self.assertEqual(line.quantity_returned, 4.0)
        # Pendiente real: -4. Antes del fix la devolución lo llevaba a -8 y descontaba 800.
        self.assertEqual(self._credit_taken(), 0.0)
