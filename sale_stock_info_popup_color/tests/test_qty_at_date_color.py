from datetime import timedelta

from odoo import Command, fields
from odoo.tests import Form, HttpCase, tagged


@tagged("post_install", "-at_install")
class TestQtyAtDateColor(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        now = fields.Datetime.now()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.partner = cls.env["res.partner"].create({"name": "Popup Color Customer"})
        names = ["Overdue", "On Time", "Late", "Received", "Partial"]
        products = cls.env["product.product"].create(
            [{"name": f"Popup Color {name}", "is_storable": True} for name in names]
        )
        cls.products = dict(zip(names, products, strict=True))
        cls.env["stock.quant"]._update_available_quantity(cls.products["Partial"], cls.warehouse.lot_stock_id, 5)

        cls.receipts = {
            "Overdue": cls._create_receipt(cls.products["Overdue"], 10, now - timedelta(days=1)),
            "On Time": cls._create_receipt(cls.products["On Time"], 10, now + timedelta(days=1)),
            "Late": cls._create_receipt(cls.products["Late"], 10, now + timedelta(days=20)),
            "Received": cls._create_receipt(cls.products["Received"], 10, now - timedelta(days=1)),
            "Partial": cls._create_receipt(cls.products["Partial"], 5, now - timedelta(days=1)),
        }

        commitment = now + timedelta(days=10)
        cls.sale_order = cls._create_sale(
            [cls.products[name] for name in ("Overdue", "On Time", "Late", "Received")], commitment
        )
        cls.partial_order = cls._create_sale([cls.products["Partial"]], commitment)

        cls.receipts["Received"].move_ids.quantity = 10
        cls.receipts["Received"].button_validate()

        delivery = cls.partial_order.picking_ids
        res = delivery.button_validate()
        Form(cls.env[res["res_model"]].with_context(**res["context"])).save().process()

    @classmethod
    def _create_receipt(cls, product, qty, date):
        receipt = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.warehouse.in_type_id.id,
                "partner_id": cls.partner.id,
                "move_ids": [
                    Command.create(
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                            "location_dest_id": cls.warehouse.lot_stock_id.id,
                        }
                    )
                ],
            }
        )
        receipt.action_confirm()
        receipt.scheduled_date = date
        return receipt

    @classmethod
    def _create_sale(cls, products, commitment):
        order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "warehouse_id": cls.warehouse.id,
                "commitment_date": commitment,
                "order_line": [Command.create({"product_id": p.id, "product_uom_qty": 10}) for p in products],
            }
        )
        order.action_confirm()
        return order

    def _line(self, name):
        return (self.sale_order | self.partial_order).order_line.filtered(
            lambda line: line.product_id == self.products[name]
        )

    def test_icon_red_with_overdue_receipt(self):
        today = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # The overdue receipt covers the demand, so the core alone does not flag it
        overdue = self._line("Overdue")
        self.assertGreaterEqual(overdue.free_qty_today, overdue.qty_to_deliver)
        self.assertLess(overdue.forecast_expected_date, today)
        partial = self._line("Partial")
        self.assertEqual(partial.qty_delivered, 5)
        self.assertLess(partial.forecast_expected_date, today)
        self.assertFalse(self._line("Received").forecast_expected_date)

        view = self.env["ir.ui.view"].create(
            {
                "name": "sale_stock_info_popup_color test lines",
                "model": "sale.order.line",
                "type": "list",
                "arch": '<list><field name="product_id"/><field name="product_uom_qty"/>'
                '<widget name="qty_at_date_widget"/></list>',
            }
        )
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Popup color lines",
                "res_model": "sale.order.line",
                "view_mode": "list",
                "view_id": view.id,
                "domain": [("order_id", "in", (self.sale_order | self.partial_order).ids)],
            }
        )
        self.start_tour(f"/odoo/action-{action.id}", "sale_stock_info_popup_color_tour", login="admin")
