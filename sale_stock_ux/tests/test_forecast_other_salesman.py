from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestForecastOtherSalesman(TransactionCase):
    """El pronosticado de un producto no debe romper por una OV de otro vendedor.

    Un vendedor con "solo mostrar documentos propios" abría el pronosticado y le
    saltaba un AccessError sobre `sale.order`: `sale_stock` lee monto, moneda y
    cliente de la OV del remito sin sudo. Solo se manifiesta cuando el movimiento
    saliente no tiene `sale_line_id` (una línea agregada a mano al remito), porque
    ahí el `sudo()` de `_get_source_document` no trae la OV a la caché. Ticket 127167.
    """

    def setUp(self):
        super().setUp()
        self.warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        self.customer_location = self.env.ref("stock.stock_location_customers")
        self.partner = self.env["res.partner"].create({"name": "Cliente pronosticado", "customer_rank": 1})
        self.product_so = self._make_product("Producto de la OV")
        self.product_manual = self._make_product("Producto agregado al remito")
        self.salesman_a = self._make_salesman("salesman_a_127167")
        self.salesman_b = self._make_salesman("salesman_b_127167")

    def _make_product(self, name):
        return self.env["product.product"].create({"name": name, "type": "consu", "is_storable": True})

    def _make_salesman(self, login):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "company_id": self.env.company.id,
                "company_ids": [Command.set([self.env.company.id])],
                "groups_id": [
                    Command.link(self.env.ref("sales_team.group_sale_salesman").id),
                    Command.link(self.env.ref("stock.group_stock_user").id),
                ],
            }
        )

    def test_forecast_with_move_without_sale_line(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "user_id": self.salesman_a.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [Command.create({"product_id": self.product_so.id, "product_uom_qty": 3})],
            }
        )
        # El remito se arma a mano en lugar de confirmar la orden: así el caso no
        # depende de las excepciones de venta ni de las rutas de la base.
        group = self.env["procurement.group"].create({"name": order.name, "sale_id": order.id})
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "partner_id": self.partner.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
                "group_id": group.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.product_manual.name,
                "picking_id": picking.id,
                "product_id": self.product_manual.id,
                "product_uom_qty": 2,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": picking.company_id.id,
                "group_id": group.id,
            }
        )
        picking.action_confirm()
        self.assertEqual(picking.sale_id, order)
        self.assertFalse(move.sale_line_id)

        self.assertFalse(order.with_user(self.salesman_b).has_access("read"))

        # La caché tiene la OV cargada como superusuario; sin invalidar no se ejerce la regla.
        self.env.invalidate_all()
        report = (
            self.env["stock.forecasted_product_product"]
            .with_user(self.salesman_b)
            .with_context(warehouse=self.warehouse.id)
        )
        lines = report.get_report_values(docids=self.product_manual.ids)["docs"]["lines"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["move_out"]["picking_id"]["sale_id"]["id"], order.id)
