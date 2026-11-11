##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase

STOCK_FIELDS = [
    "qty_to_deliver",
    "display_qty_widget",
    "qty_available_today",
    "free_qty_today",
    "virtual_available_at_date",
    "scheduled_date",
    "forecast_expected_date",
    "is_mto",
]


class TestDistributorKit(TransactionCase):
    """The portal distributor does not read the bills of materials, but it has to be able to
    open an order with a kit: the stock fields of the line look at the BoM to know if the
    product is a kit, so the module computes them as superuser for the distributor."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.distributor = cls.env["res.users"].create(
            {
                "name": "Distribuidor mrp test",
                "login": "distributor_mrp_test",
                "company_id": cls.env.ref("base.main_company").id,
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_portal").id,
                            cls.env.ref("portal_backend.group_portal_backend").id,
                            cls.env.ref("portal_sale_distributor.group_portal_backend_distributor").id,
                        ],
                    )
                ],
            }
        )
        Product = cls.env["product.product"]
        warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.component_a = Product.create({"name": "Componente A test", "is_storable": True})
        cls.component_b = Product.create({"name": "Componente B test", "is_storable": True})
        cls.kit = Product.create({"name": "Kit test", "type": "consu", "list_price": 100})
        cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit.product_tmpl_id.id,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.component_a.id, "product_qty": 2}),
                    (0, 0, {"product_id": cls.component_b.id, "product_qty": 1}),
                ],
            }
        )
        for component in (cls.component_a, cls.component_b):
            cls.env["stock.quant"]._update_available_quantity(component, warehouse.lot_stock_id, 50)
        cls.partner = cls.distributor.partner_id

    def _new_request(self):
        """What was computed as superuser stays in the cache and is read back without checking
        the access, so the test would never see the AccessError of a new request."""
        self.env.flush_all()
        self.env.invalidate_all()

    def _order(self, confirm=False, deliver=False):
        order = (
            self.env["sale.order"]
            .with_user(self.distributor)
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [(0, 0, {"product_id": self.kit.id, "product_uom_qty": 3})],
                }
            )
        )
        if confirm:
            order.action_confirm_distributor()
        if deliver:
            picking = order.sudo().picking_ids
            picking.action_assign()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
            picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
        return order

    def test_distributor_does_not_read_the_boms(self):
        bom = self.env["mrp.bom"].search([("product_tmpl_id", "=", self.kit.product_tmpl_id.id)])
        self.assertFalse(bom.with_user(self.distributor).has_access("read"))
        self.assertFalse(bom.bom_line_ids.with_user(self.distributor).has_access("read"))

    def test_distributor_reads_the_stock_fields_of_a_kit_line(self):
        for state, kwargs in (
            ("presupuesto", {}),
            ("confirmado", {"confirm": True}),
            ("entregado", {"confirm": True, "deliver": True}),
        ):
            with self.subTest(state):
                line = self._order(**kwargs).order_line.with_user(self.distributor)
                self._new_request()
                # un AccessError acá es el fallo que cubre el módulo
                self.assertEqual(len(line.read(STOCK_FIELDS)), 1)

    def test_distributor_sees_what_was_delivered_of_a_kit(self):
        order = self._order(confirm=True, deliver=True).with_user(self.distributor)
        self._new_request()
        spec = {
            "state": {},
            "delivery_status": {},
            "order_line": {"fields": {"qty_delivered": {}, **dict.fromkeys(STOCK_FIELDS, {})}},
        }
        values = order.web_read(spec)[0]
        self.assertEqual(values["order_line"][0]["qty_delivered"], 3.0)
        self.assertEqual(values["delivery_status"], "full")
