##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleBarcode(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("uom.group_uom")
        cls.unit = cls.env.ref("uom.product_uom_unit")
        cls.packaging_uom = cls.env["uom.uom"].create(
            {
                "name": "Pack of 12",
                "relative_factor": 12.0,
                "relative_uom_id": cls.unit.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Scannable product",
                "list_price": 100.0,
                "barcode": "PRODUCT_BARCODE",
                "uom_id": cls.unit.id,
                "uom_ids": [(6, 0, cls.packaging_uom.ids)],
            }
        )
        cls.env["product.uom"].create(
            {
                "product_id": cls.product.id,
                "uom_id": cls.packaging_uom.id,
                "barcode": "PACKAGING_BARCODE",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Scannable partner"})

    def _scan(self, *barcodes):
        """Return the order lines resulting from scanning barcodes on a new order."""
        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.partner
        for barcode in barcodes:
            order_form._barcode_scanned = barcode
        return order_form.save().order_line

    def test_scan_product(self):
        lines = self._scan(*["PRODUCT_BARCODE"] * 15)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_uom_qty, 15.0)
        self.assertEqual(lines.product_uom_id, self.unit)

    def test_scan_packaging(self):
        lines = self._scan(*["PACKAGING_BARCODE"] * 3)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_uom_qty, 3.0)
        self.assertEqual(lines.product_uom_id, self.packaging_uom)

    def test_scan_packaging_on_line_sold_by_unit(self):
        """The packaging content is added to the line, in the unit of that line."""
        lines = self._scan("PRODUCT_BARCODE", "PRODUCT_BARCODE", "PACKAGING_BARCODE")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_uom_qty, 14.0)
        self.assertEqual(lines.product_uom_id, self.unit)

    def test_scan_product_on_line_sold_by_packaging(self):
        """A single unit adds a whole packaging instead of a fraction of one."""
        lines = self._scan("PACKAGING_BARCODE", "PRODUCT_BARCODE")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_uom_qty, 2.0)
        self.assertEqual(lines.product_uom_id, self.packaging_uom)

    def test_scan_product_on_line_with_packaging_set_manually(self):
        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.partner
        order_form._barcode_scanned = "PRODUCT_BARCODE"
        with order_form.order_line.edit(0) as line:
            line.product_uom_id = self.packaging_uom
            line.product_uom_qty = 1.0
        order_form._barcode_scanned = "PRODUCT_BARCODE"
        lines = order_form.save().order_line
        self.assertEqual(lines.product_uom_qty, 2.0)
        self.assertEqual(lines.product_uom_id, self.packaging_uom)

    def test_scan_packaging_not_sellable(self):
        """A packaging not available for sale falls back to the product unit."""
        self.product.uom_ids = [(5, 0, 0)]
        lines = self._scan("PACKAGING_BARCODE")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_uom_qty, 12.0)
        self.assertEqual(lines.product_uom_id, self.unit)

    def test_scan_unknown_barcode(self):
        order = self.env["sale.order"].new({"partner_id": self.partner.id})
        result = order.on_barcode_scanned("UNKNOWN_BARCODE")
        self.assertIn("warning", result)
        self.assertFalse(order.order_line)
