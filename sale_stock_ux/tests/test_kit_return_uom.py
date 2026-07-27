from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKitReturnUom(TransactionCase):
    """Devolver un kit cuyos componentes están en otra categoría de UdM no debe romper.

    Un kit (BoM phantom) vendido en unidades con su componente en litros explota
    en movimientos de stock en litros. Al validar la devolución se convertía la
    UdM del movimiento a la de la línea y, al ser categorías distintas, el
    `_compute_quantity` nativo de `uom` levantaba UserError. Para kits ese valor
    lo pisa después `_compute_kit_quantities`, así que la conversión nunca hizo
    falta. Ver ticket 123147.
    """

    def setUp(self):
        super().setUp()
        # El escenario necesita sale_mrp: mrp explota el kit, pero el cálculo de
        # cantidades entregadas/devueltas de kits lo aporta sale_mrp.
        if not self.env["ir.module.module"].search_count([("name", "=", "sale_mrp"), ("state", "=", "installed")]):
            self.skipTest("sale_mrp no está instalado")

        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        warehouse.delivery_steps = "ship_only"

        self.partner = self.env["res.partner"].create({"name": "Test Partner Kit", "customer_rank": 1})

        self.uom_unit = self.env.ref("uom.product_uom_unit")
        self.uom_litre = self.env.ref("uom.product_uom_litre")

        self.component = self.env["product.product"].create(
            {
                "name": "Esencia (litros)",
                "type": "consu",
                "is_storable": True,
                "uom_id": self.uom_litre.id,
                "uom_po_id": self.uom_litre.id,
                "list_price": 50.0,
            }
        )
        self.kit = self.env["product.product"].create(
            {
                "name": "Carga fragancia (kit en unidades)",
                "type": "consu",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
                "invoice_policy": "delivery",
                "list_price": 100.0,
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.kit.product_tmpl_id.id,
                "product_id": self.kit.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom_unit.id,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": self.component.id, "product_qty": 0.15, "product_uom_id": self.uom_litre.id})
                ],
            }
        )

        if self.env["sale.order"]._fields.get("ignore_exception"):
            self.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

        self.sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [(0, 0, {"product_id": self.kit.id, "product_uom_qty": 1.0, "price_unit": 100.0})],
            }
        )
        self.sale_order.action_confirm()
        self.order_line = self.sale_order.order_line
        self.delivery = self.sale_order.picking_ids

    def _validate(self, picking):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.move_line_ids.unlink()
            move.quantity = move.product_uom_qty
            move.picked = True
        picking._action_done()

    def _make_return(self, picking, to_refund=True):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_ids=picking.ids, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.to_refund = to_refund
            line.quantity = line.move_id.quantity
        action = wizard.action_create_returns()
        return self.env["stock.picking"].browse(action["res_id"])

    def test_delivery_of_kit_explodes_into_component_uom(self):
        """El kit se explota en movimientos del componente, en litros."""
        self.assertEqual(self.delivery.move_ids.product_id, self.component)
        self.assertEqual(self.delivery.move_ids.product_uom, self.uom_litre)
        self._validate(self.delivery)
        self.assertEqual(self.delivery.state, "done")
        self.assertEqual(self.order_line.qty_delivered, 1.0)
        self.assertEqual(self.order_line.quantity_returned, 0.0)

    def test_return_of_kit_with_component_in_other_uom_category(self):
        """Validar la devolución no debe levantar UserError por conversión de UdM."""
        # Precondición del caso: el componente vive en otra categoría que el kit.
        self.assertNotEqual(self.uom_unit.category_id, self.uom_litre.category_id)
        self._validate(self.delivery)

        returned = self._make_return(self.delivery, to_refund=True)
        self.assertEqual(returned.move_ids.product_uom, self.uom_litre)

        # Sin el fix, esto levanta UserError desde uom._compute_quantity
        # (Unidades y Litros no comparten categoría).
        self._validate(returned)

        self.assertEqual(returned.state, "done")
        # La cantidad devuelta la calcula _compute_kit_quantities en unidades del kit.
        self.assertEqual(self.order_line.quantity_returned, 1.0)
        self.assertEqual(self.order_line.qty_delivered, 0.0)

    def test_return_of_kit_without_refund(self):
        """Sin 'actualizar cantidades a facturar' tampoco rompe y no descuenta."""
        self._validate(self.delivery)

        returned = self._make_return(self.delivery, to_refund=False)
        self._validate(returned)

        self.assertEqual(returned.state, "done")
        self.assertEqual(self.order_line.quantity_returned, 0.0)
