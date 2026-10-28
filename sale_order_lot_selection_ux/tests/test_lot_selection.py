<<<<<<< ed2214e5895bd52ea2b7c7519d70665ce58af97b
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from lxml import etree
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLotSelectionUx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.product = cls.env["product.product"].create(
            {"name": "Lot Selection UX Product", "is_storable": True, "tracking": "lot"}
        )
        cls.context = {"from_sale_line": True, "warehouse_id": cls.warehouse.id}

    def _lot(self, name, product=None):
        return self.env["stock.lot"].create({"name": name, "product_id": (product or self.product).id})

    def _stock(self, lot, quantity, reserved=0.0, location=None):
        location = location or self.stock_location
        product = lot.product_id
        self.env["stock.quant"]._update_available_quantity(product, location, quantity, lot_id=lot)
        if reserved:
            self.env["stock.quant"]._update_reserved_quantity(product, location, reserved, lot_id=lot)

    def _display_name(self, lot, **context):
        # display_name is not stored and the cache does not know about the context
        self.env.invalidate_all()
        return lot.with_context(**context).display_name

    def test_display_name_shows_available_quantity_and_unit(self):
        lot_free = self._lot("LOT-FREE")
        lot_reserved = self._lot("LOT-RESERVED")
        self._stock(lot_free, 5.0)
        self._stock(lot_reserved, 3.0, reserved=3.0)
        unit = self.product.uom_id.name

        self.assertEqual(self._display_name(lot_free, **self.context), "LOT-FREE (5.0 %s) " % unit)
        self.assertEqual(self._display_name(lot_reserved, **self.context), "LOT-RESERVED (0.0 %s) " % unit)

    def test_display_name_discounts_the_reserved_quantity(self):
        lot = self._lot("LOT-PARTIAL")
        self._stock(lot, 5.0, reserved=2.0)

        self.assertEqual(self._display_name(lot, **self.context), "LOT-PARTIAL (3.0 %s) " % self.product.uom_id.name)

    def test_display_name_counts_the_stock_one_level_below_the_warehouse_stock(self):
        shelf = self.env["stock.location"].create(
            {"name": "Lot Selection UX Shelf", "location_id": self.stock_location.id, "usage": "internal"}
        )
        lot = self._lot("LOT-SHELF")
        self._stock(lot, 4.0, location=shelf)

        self.assertEqual(self._display_name(lot, **self.context), "LOT-SHELF (4.0 %s) " % self.product.uom_id.name)

    def test_display_name_is_the_plain_name_outside_the_sale_line(self):
        lot = self._lot("LOT-PLAIN")
        self._stock(lot, 5.0)

        self.assertEqual(self._display_name(lot), "LOT-PLAIN")
        self.assertEqual(self._display_name(lot, from_sale_line=True), "LOT-PLAIN")
        self.assertEqual(self._display_name(lot, warehouse_id=self.warehouse.id), "LOT-PLAIN")

    def test_the_lot_filter_is_the_one_of_sale_order_lot_selection(self):
        # sale_order_lot_selection filters the lots with the domain_lot_id of the field: a domain on
        # the view, as this module had, overrides it and leaves its settings without effect
        self.assertNotIn("available_lot_ids", self.env["sale.order.line"]._fields)
        arch = self.env["sale.order"].get_view(view_id=self.env.ref("sale.view_order_form").id)["arch"]
        nodes = [
            node
            for node in etree.fromstring(arch.encode()).xpath("//field[@name='order_line']//field[@name='lot_id']")
            if "from_sale_line" in (node.get("context") or "")
        ]

        self.assertEqual(len(nodes), 2, "the list and the form of the sale line")
        for node in nodes:
            self.assertIsNone(node.get("domain"))

    def test_the_context_of_the_lot_keeps_the_default_product_of_sale_order_lot_selection(self):
        arch = self.env["sale.order"].get_view(view_id=self.env.ref("sale.view_order_form").id)["arch"]
        nodes = [
            node
            for node in etree.fromstring(arch.encode()).xpath("//field[@name='order_line']//field[@name='lot_id']")
            if "from_sale_line" in (node.get("context") or "")
        ]

        self.assertTrue(nodes)
        for node in nodes:
            self.assertIn("default_product_id", node.get("context"))
            self.assertIn("list_view_ref", node.get("context"))
||||||| dd1333254af5996a3ffa9c19ff9de8a713e207c3
=======
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLotSelectionUx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.partner = cls.env["res.partner"].create({"name": "Lot Selection UX Partner"})
        cls.product = cls.env["product.product"].create(
            {"name": "Lot Selection UX Product", "is_storable": True, "tracking": "lot"}
        )
        cls.serial_product = cls.env["product.product"].create(
            {"name": "Lot Selection UX Serial Product", "is_storable": True, "tracking": "serial"}
        )
        cls.untracked_product = cls.env["product.product"].create(
            {"name": "Lot Selection UX Untracked Product", "is_storable": True}
        )
        cls.context = {"from_sale_line": True, "warehouse_id": cls.warehouse.id}

    def _lot(self, name, product=None):
        return self.env["stock.lot"].create({"name": name, "product_id": (product or self.product).id})

    def _stock(self, lot, quantity, reserved=0.0, location=None):
        location = location or self.stock_location
        product = lot.product_id
        self.env["stock.quant"]._update_available_quantity(product, location, quantity, lot_id=lot)
        if reserved:
            self.env["stock.quant"]._update_reserved_quantity(product, location, reserved, lot_id=lot)

    def _sale_line(self, product=None):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [Command.create({"product_id": (product or self.product).id, "product_uom_qty": 1.0})],
            }
        )
        return order.order_line

    def _display_name(self, lot, **context):
        # display_name is not stored and the cache does not know about the context
        self.env.invalidate_all()
        return lot.with_context(**context).display_name

    def test_display_name_shows_available_quantity_and_unit(self):
        lot_free = self._lot("LOT-FREE")
        lot_reserved = self._lot("LOT-RESERVED")
        self._stock(lot_free, 5.0)
        self._stock(lot_reserved, 3.0, reserved=3.0)
        unit = self.product.uom_id.name

        self.assertEqual(self._display_name(lot_free, **self.context), "LOT-FREE (5.0 %s) " % unit)
        self.assertEqual(self._display_name(lot_reserved, **self.context), "LOT-RESERVED (0.0 %s) " % unit)

    def test_display_name_discounts_the_reserved_quantity(self):
        lot = self._lot("LOT-PARTIAL")
        self._stock(lot, 5.0, reserved=2.0)

        self.assertEqual(self._display_name(lot, **self.context), "LOT-PARTIAL (3.0 %s) " % self.product.uom_id.name)

    def test_display_name_counts_the_stock_one_level_below_the_warehouse_stock(self):
        shelf = self.env["stock.location"].create(
            {"name": "Lot Selection UX Shelf", "location_id": self.stock_location.id, "usage": "internal"}
        )
        lot = self._lot("LOT-SHELF")
        self._stock(lot, 4.0, location=shelf)

        self.assertEqual(self._display_name(lot, **self.context), "LOT-SHELF (4.0 %s) " % self.product.uom_id.name)

    def test_display_name_is_the_plain_name_outside_the_sale_line(self):
        lot = self._lot("LOT-PLAIN")
        self._stock(lot, 5.0)

        self.assertEqual(self._display_name(lot), "LOT-PLAIN")
        self.assertEqual(self._display_name(lot, from_sale_line=True), "LOT-PLAIN")
        self.assertEqual(self._display_name(lot, warehouse_id=self.warehouse.id), "LOT-PLAIN")

    def test_available_lots_exclude_the_reserved_and_the_ones_without_stock(self):
        lot_free = self._lot("LOT-FREE")
        lot_reserved = self._lot("LOT-RESERVED")
        self._lot("LOT-EMPTY")
        self._stock(lot_free, 5.0)
        self._stock(lot_reserved, 3.0, reserved=3.0)

        self.assertEqual(self._sale_line().available_lot_ids, lot_free)

    def test_available_lots_include_the_ones_below_the_warehouse_stock(self):
        shelf = self.env["stock.location"].create(
            {"name": "Lot Selection UX Shelf", "location_id": self.stock_location.id, "usage": "internal"}
        )
        lot = self._lot("LOT-SHELF")
        self._stock(lot, 4.0, location=shelf)

        self.assertEqual(self._sale_line().available_lot_ids, lot)

    def test_available_lots_of_a_serial_product(self):
        serial_free = self._lot("SN-FREE", self.serial_product)
        serial_reserved = self._lot("SN-RESERVED", self.serial_product)
        self._stock(serial_free, 1.0)
        self._stock(serial_reserved, 1.0, reserved=1.0)

        self.assertEqual(self._sale_line(self.serial_product).available_lot_ids, serial_free)

    def test_no_available_lots_for_a_product_without_tracking(self):
        self.env["stock.quant"]._update_available_quantity(self.untracked_product, self.stock_location, 5.0)

        self.assertFalse(self._sale_line(self.untracked_product).available_lot_ids)
>>>>>>> f8ae5c0cdd15cfc9fd3abe7d6357070da26ca338
