# © 2026 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from unittest.mock import patch

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.sale.models.sale_order import SaleOrder as BaseSaleOrder
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger
from psycopg2 import IntegrityError


@tagged("sale_require_purchase_order_number", "post_install", "-at_install")
class TestPurchaseOrderNumber(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("sales_team.group_sale_manager") + cls.env.ref(
            "stock.group_stock_manager"
        )
        cls.partner = cls.partner_a
        cls.partner.require_purchase_order_number = True
        cls.partner_free = cls.partner_b
        cls.product = cls.product_a
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.customers = cls.env.ref("stock.stock_location_customers")
        cls.suppliers = cls.env.ref("stock.stock_location_suppliers")

    def _create_so(self, partner=None, po_number=False):
        return self.env["sale.order"].create(
            {
                "partner_id": (partner or self.partner).id,
                "purchase_order_number": po_number,
                "order_line": [
                    Command.create({"product_id": self.product.id, "product_uom_qty": 1, "price_unit": 100.0}),
                ],
            }
        )

    def _create_invoice(self, partner=None, po_number=False):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": (partner or self.partner).id,
                "invoice_date": fields.Date.today(),
                "purchase_order_number": po_number,
                "invoice_line_ids": [
                    Command.create({"product_id": self.product.id, "quantity": 1, "price_unit": 100.0}),
                ],
            }
        )

    def _create_picking(self, partner=None, outgoing=True, po_number=False):
        picking_type = self.warehouse.out_type_id if outgoing else self.warehouse.in_type_id
        src, dest = (
            (self.warehouse.lot_stock_id, self.customers) if outgoing else (self.suppliers, self.warehouse.lot_stock_id)
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "partner_id": (partner or self.partner).id,
                "location_id": src.id,
                "location_dest_id": dest.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "location_id": src.id,
                            "location_dest_id": dest.id,
                        }
                    ),
                ],
            }
        )
        if po_number:
            picking.purchase_order_number = po_number
        picking.action_confirm()
        picking.move_ids.write({"quantity": 1, "picked": True})
        return picking

    # 1. Confirmación de la orden de venta
    def test_01_confirm_requires_number(self):
        order_without_number = self._create_so()
        with self.assertRaises(UserError):
            order_without_number.action_confirm()
        self.assertEqual(order_without_number.state, "draft")

        order_with_number = self._create_so(po_number="PO-1")
        order_with_number.action_confirm()
        self.assertEqual(order_with_number.state, "sale")

    # 2. Unicidad por cliente
    def test_02_number_is_unique_per_partner(self):
        self._create_so(po_number="PO-UNIQUE")
        # otro cliente puede repetir el número
        self._create_so(partner=self.partner_free, po_number="PO-UNIQUE")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self._create_so(po_number="PO-UNIQUE")

    # 3. La factura recibe el número de la orden
    def test_03_invoice_gets_number_from_order(self):
        order = self._create_so(po_number="PO-INV")
        order.action_confirm()
        invoice = order._create_invoices()
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.purchase_order_number, "PO-INV")

    # 4. Varias órdenes en una factura (o una factura por orden)
    def test_04_invoice_from_many_orders(self):
        order_a = self._create_so(po_number="PO-A")
        order_b = self._create_so(po_number="PO-B")
        orders = order_a | order_b
        orders.action_confirm()

        invoice = orders._create_invoices()
        self.assertEqual(len(invoice), 1, "Dos órdenes del mismo cliente van en una sola factura")
        self.assertEqual(set(invoice.purchase_order_number.split(", ")), {"PO-A", "PO-B"})

        # con `grouped=True` sale una factura por orden y cada una lleva su número
        order_c = self._create_so(po_number="PO-C")
        order_d = self._create_so(po_number="PO-D")
        orders = order_c | order_d
        orders.action_confirm()
        invoices = orders._create_invoices(grouped=True)
        self.assertEqual(len(invoices), 2)
        numbers_by_origin = {inv.invoice_origin: inv.purchase_order_number for inv in invoices}
        self.assertEqual(numbers_by_origin, {order_c.name: "PO-C", order_d.name: "PO-D"})

    def test_04b_invoice_flags_reach_the_standard_method(self):
        """`final` y `grouped` tienen que llegar al método estándar, sin importar el orden de la firma."""
        order_final = self._create_so(po_number="PO-FLAGS-1")
        order_grouped = self._create_so(po_number="PO-FLAGS-2")
        (order_final | order_grouped).action_confirm()
        original = BaseSaleOrder._create_invoices
        received = []

        def spy(orders, *args, **kwargs):
            received.append(inspect.signature(original).bind(orders, *args, **kwargs).arguments)
            return original(orders, *args, **kwargs)

        with patch.object(BaseSaleOrder, "_create_invoices", spy):
            order_final._create_invoices(final=True)
            order_grouped._create_invoices(grouped=True)
        self.assertEqual(len(received), 2)
        self.assertTrue(received[0].get("final"))
        self.assertFalse(received[0].get("grouped"))
        self.assertTrue(received[1].get("grouped"))
        self.assertFalse(received[1].get("final"))

    # 5. Publicar la factura
    def test_05_post_invoice_requires_number(self):
        invoice_without_number = self._create_invoice()
        with self.assertRaises(UserError):
            invoice_without_number.action_post()

        invoice_with_number = self._create_invoice(po_number="PO-POST")
        invoice_with_number.action_post()
        self.assertEqual(invoice_with_number.state, "posted")

    # 6. Entrega
    def test_06_picking_done_requires_number(self):
        picking_without_number = self._create_picking()
        self.assertFalse(picking_without_number.purchase_order_number)
        with self.assertRaises(UserError):
            picking_without_number._action_done()

        picking_with_number = self._create_picking(po_number="PO-MANUAL")
        self.assertEqual(picking_with_number.manual_purchase_order_number, "PO-MANUAL")
        picking_with_number._action_done()
        self.assertEqual(picking_with_number.state, "done")

    def test_06b_picking_number_comes_from_order_and_manual_wins(self):
        order = self._create_so(po_number="PO-SO")
        order.action_confirm()
        picking = order.picking_ids
        self.assertEqual(picking.purchase_order_number, "PO-SO")
        picking.purchase_order_number = "PO-MAN"
        self.assertEqual(picking.purchase_order_number, "PO-MAN")
        self.assertEqual(order.purchase_order_number, "PO-SO")

    # 7. Sin la marca en el cliente no se exige nada
    def test_07_nothing_required_without_flag(self):
        order = self._create_so(partner=self.partner_free)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

        invoice = self._create_invoice(partner=self.partner_free)
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

        picking = self._create_picking(partner=self.partner_free)
        picking._action_done()
        self.assertEqual(picking.state, "done")

    def test_07b_incoming_picking_is_not_blocked(self):
        picking = self._create_picking(outgoing=False)
        picking._action_done()
        self.assertEqual(picking.state, "done")
