from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockInfoBatching(TransactionCase):
    """`stock_by_location` y `total_reserved_quantity` se resuelven en lote.

    Ambos campos viven en la vista de líneas del pedido, así que se recalculan
    en cada onchange de la cabecera. Consultaban `stock.quant` una vez por línea:
    en una orden de 293 líneas eso daba ~1.700 consultas y ~4,6 s. Ver ticket
    124420 (backport de ingadhoc/sale#1762).
    """

    def setUp(self):
        super().setUp()
        self.uom_unit = self.env.ref("uom.product_uom_unit")
        self.uom_dozen = self.env.ref("uom.product_uom_dozen")

        self.warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        self.loc_a = self.env["stock.location"].create(
            {"name": "Test Batching A", "usage": "internal", "location_id": self.warehouse.lot_stock_id.id}
        )
        self.loc_b = self.env["stock.location"].create(
            {"name": "Test Batching B", "usage": "internal", "location_id": self.warehouse.lot_stock_id.id}
        )

        self.partner = self.env["res.partner"].create({"name": "Test Partner Batching", "customer_rank": 1})

        # 10 en A con 4 reservadas (6 disponibles) y 5 en B.
        self.product_a = self._make_product("Producto A", [(self.loc_a, 10, 4), (self.loc_b, 5, 0)])
        # Solo en B, sin reservas.
        self.product_b = self._make_product("Producto B", [(self.loc_b, 7, 0)])
        # Sin quants en ninguna ubicación.
        self.product_c = self._make_product("Producto C")

    def _make_product(self, name, quants=()):
        product = self.env["product.product"].create(
            {
                "name": name,
                "type": "consu",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
            }
        )
        for location, quantity, reserved in quants:
            self.env["stock.quant"]._update_available_quantity(product, location, quantity)
            if reserved:
                self.env["stock.quant"]._update_reserved_quantity(product, location, reserved)
        return product

    def _make_order(self, line_vals):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [(0, 0, vals) for vals in line_vals],
            }
        )

    def _query_count(self, lines, field_name):
        """Consultas que cuesta recalcular `field_name` sobre `lines`, ya calientes.

        El primer cálculo llena la cache de los campos que el compute lee
        (producto, UdM, ubicaciones); invalidando solo el campo computado, lo
        que se mide después es el acceso a `stock.quant` y nada más.
        """
        lines.mapped(field_name)
        lines.invalidate_recordset([field_name])
        before = self.env.cr.sql_log_count
        lines.mapped(field_name)
        return self.env.cr.sql_log_count - before

    def _expected_line(self, location, qty, uom):
        return f"{location.display_name}: {qty:.2f} {uom.name}"

    def test_stock_by_location_values_per_line(self):
        """Cada línea muestra el stock disponible de SU producto, sin cruzarse."""
        order = self._make_order(
            [
                {"product_id": self.product_a.id, "product_uom_qty": 1.0},
                {"product_id": self.product_b.id, "product_uom_qty": 1.0},
                {"product_id": self.product_c.id, "product_uom_qty": 1.0},
                {"display_type": "line_section", "name": "Sección"},
            ]
        )
        line_a, line_b, line_c, section = order.order_line

        # Producto A: 6 disponibles en A (10 menos 4 reservadas) y 5 en B.
        self.assertEqual(
            set(line_a.stock_by_location.split("\n")),
            {
                self._expected_line(self.loc_a, 6.0, self.uom_unit),
                self._expected_line(self.loc_b, 5.0, self.uom_unit),
            },
        )
        # Producto B: solo la ubicación donde tiene stock, sin arrastrar la de A.
        self.assertEqual(line_b.stock_by_location, self._expected_line(self.loc_b, 7.0, self.uom_unit))
        self.assertEqual(line_c.stock_by_location, "")
        self.assertEqual(section.stock_by_location, "")

    def test_stock_by_location_converts_uom_per_line(self):
        """Dos líneas del mismo producto en distinta UdM no comparten el valor convertido."""
        product = self._make_product("Producto Docenas", [(self.loc_a, 24, 0)])
        order = self._make_order(
            [
                {"product_id": product.id, "product_uom_qty": 1.0, "product_uom": self.uom_unit.id},
                {"product_id": product.id, "product_uom_qty": 1.0, "product_uom": self.uom_dozen.id},
            ]
        )
        line_units, line_dozens = order.order_line

        self.assertEqual(line_units.stock_by_location, self._expected_line(self.loc_a, 24.0, self.uom_unit))
        self.assertEqual(line_dozens.stock_by_location, self._expected_line(self.loc_a, 2.0, self.uom_dozen))

    def test_stock_by_location_queries_do_not_scale_with_lines(self):
        """El costo del cálculo no depende de cuántas líneas tenga el pedido."""
        few = [self._make_product(f"Producto pocos {i}", [(self.loc_a, 5, 0)]) for i in range(3)]
        many = [self._make_product(f"Producto muchos {i}", [(self.loc_a, 5, 0)]) for i in range(12)]
        order_few = self._make_order([{"product_id": p.id, "product_uom_qty": 1.0} for p in few])
        order_many = self._make_order([{"product_id": p.id, "product_uom_qty": 1.0} for p in many])

        queries_few = self._query_count(order_few.order_line, "stock_by_location")
        queries_many = self._query_count(order_many.order_line, "stock_by_location")

        self.assertEqual(
            queries_many,
            queries_few,
            "stock_by_location vuelve a consultar stock.quant por línea (N+1)",
        )

    def test_total_reserved_quantity_only_counts_warehouse_stock(self):
        """Suma lo reservado bajo la ubicación del almacén del pedido, y nada más."""
        outside = self.env["stock.location"].create(
            {
                "name": "Test Batching Fuera",
                "usage": "internal",
                "location_id": self.env.ref("stock.stock_location_locations").id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(self.product_a, outside, 20)
        self.env["stock.quant"]._update_reserved_quantity(self.product_a, outside, 9)

        order = self._make_order(
            [
                {"product_id": self.product_a.id, "product_uom_qty": 1.0},
                {"product_id": self.product_c.id, "product_uom_qty": 1.0},
                {"display_type": "line_section", "name": "Sección"},
            ]
        )
        line_a, line_c, section = order.order_line

        # Las 4 reservadas en A; las 9 de la ubicación externa quedan afuera.
        self.assertAlmostEqual(line_a.total_reserved_quantity, 4.0)
        self.assertAlmostEqual(line_c.total_reserved_quantity, 0.0)
        self.assertAlmostEqual(section.total_reserved_quantity, 0.0)

    def test_total_reserved_quantity_queries_do_not_scale_with_lines(self):
        """El costo del cálculo no depende de cuántas líneas tenga el pedido."""
        few = [self._make_product(f"Reservado pocos {i}", [(self.loc_a, 5, 2)]) for i in range(3)]
        many = [self._make_product(f"Reservado muchos {i}", [(self.loc_a, 5, 2)]) for i in range(12)]
        order_few = self._make_order([{"product_id": p.id, "product_uom_qty": 1.0} for p in few])
        order_many = self._make_order([{"product_id": p.id, "product_uom_qty": 1.0} for p in many])

        queries_few = self._query_count(order_few.order_line, "total_reserved_quantity")
        queries_many = self._query_count(order_many.order_line, "total_reserved_quantity")

        self.assertEqual(
            queries_many,
            queries_few,
            "total_reserved_quantity vuelve a consultar stock.quant por línea (N+1)",
        )
