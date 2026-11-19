##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestPurchaseOrderReference(ValuationReconciliationTestCommon):
    # not on TestL10nClEdiStockCommon: it writes fields of modules that are not dependencies
    @classmethod
    @ValuationReconciliationTestCommon.setup_country("cl")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref("sales_team.group_sale_salesman")
        cls.env.company.l10n_cl_dte_service_provider = "SIITEST"
        cls.warehouse = cls.company_data["default_warehouse"]
        cls.chilean_partner_a = cls.env["res.partner"].create(
            {
                "name": "Chilean Partner A",
                "is_company": True,
                "country_id": cls.env.ref("base.cl").id,
                "company_id": cls.env.company.id,
                "l10n_latam_identification_type_id": cls.env.ref("l10n_cl.it_RUT").id,
                "l10n_cl_sii_taxpayer_type": "1",
                "vat": "76086428-5",
            }
        )
        cls.purchase_order_doc_type = cls.env.ref("l10n_cl.dc_odc")
        cls.product = cls.env["product.product"].create(
            {"name": "Purchase order product", "is_storable": True, "list_price": 100.0}
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.warehouse.lot_stock_id, 1000)

    def _confirm_order(self, purchase_order_number, client_order_ref=False, partner=None):
        order = self.env["sale.order"].create(
            {
                "partner_id": (partner or self.chilean_partner_a).id,
                "warehouse_id": self.warehouse.id,
                "purchase_order_number": purchase_order_number,
                "client_order_ref": client_order_ref,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 4})],
            }
        )
        order.action_confirm()
        return order

    def _references(self, record):
        return record.l10n_cl_reference_ids.filtered(
            lambda ref: ref.l10n_cl_reference_doc_type_id == self.purchase_order_doc_type
        )

    def _validate(self, picking, quantity=None):
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty if quantity is None else quantity
        picking.move_ids.picked = True
        res = picking.button_validate()
        if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
            Form(self.env[res["res_model"]].with_context(**res["context"])).save().process()

    def _delivery(self, order):
        return order.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")

    def test_one_step_without_client_ref(self):
        order = self._confirm_order("OC-100")
        references = self._references(order.picking_ids)
        self.assertEqual(references.mapped("origin_doc_number"), ["OC-100"])
        self.assertEqual(references.date, order._prepare_l10n_cl_purchase_order_reference_vals()["date"])

    def test_one_step_with_client_ref(self):
        order = self._confirm_order("OC-101", client_order_ref="CLIENT-101")
        self.assertEqual(self._references(order.picking_ids).mapped("origin_doc_number"), ["OC-101"])

    def test_without_purchase_order_number_keeps_upstream(self):
        order = self._confirm_order(False, client_order_ref="CLIENT-102")
        self.assertEqual(self._references(order.picking_ids).mapped("origin_doc_number"), ["CLIENT-102"])
        order = self._confirm_order(False)
        self.assertFalse(self._references(order.picking_ids))

    def test_without_dte_service_provider(self):
        self.env.company.l10n_cl_dte_service_provider = False
        order = self._confirm_order("OC-103")
        self.assertFalse(self._references(order.picking_ids))
        self.assertFalse(self._references(order._create_invoices()))

    def test_two_steps(self):
        self.warehouse.delivery_steps = "pick_ship"
        for purchase_order_number, client_order_ref in (("OC-200", False), ("OC-201", "CLIENT-201")):
            order = self._confirm_order(purchase_order_number, client_order_ref=client_order_ref)
            pick = order.picking_ids.filtered(lambda p: p.picking_type_code == "internal")
            self.assertEqual(self._references(pick).mapped("origin_doc_number"), [purchase_order_number])
            self._validate(pick)
            self.assertEqual(
                self._references(self._delivery(order)).mapped("origin_doc_number"), [purchase_order_number]
            )

    def test_two_steps_keeps_user_edit(self):
        self.warehouse.delivery_steps = "pick_ship"
        for client_order_ref in (False, "CLIENT-202"):
            order = self._confirm_order(f"OC-202-{bool(client_order_ref)}", client_order_ref=client_order_ref)
            pick = order.picking_ids
            self._references(pick).origin_doc_number = "TYPED"
            self._validate(pick)
            self.assertEqual(self._references(self._delivery(order)).mapped("origin_doc_number"), ["TYPED"])

    def test_three_steps(self):
        self.warehouse.delivery_steps = "pick_pack_ship"
        order = self._confirm_order("OC-300")
        while pending := order.picking_ids.filtered(
            lambda p: p.picking_type_code == "internal" and p.state not in ("done", "cancel")
        ):
            self._validate(pending)
        delivery = self._delivery(order)
        self.assertTrue(delivery)
        self.assertEqual(self._references(delivery).mapped("origin_doc_number"), ["OC-300"])
        self.assertEqual(len(order.picking_ids), 3)
        for picking in order.picking_ids:
            self.assertEqual(len(self._references(picking)), 1)

    def test_backorder_keeps_reference(self):
        order = self._confirm_order("OC-400")
        picking = order.picking_ids
        self._references(picking).origin_doc_number = "TYPED"
        self._validate(picking, quantity=1)
        backorder = order.picking_ids - picking
        self.assertTrue(backorder)
        self.assertEqual(self._references(backorder).mapped("origin_doc_number"), ["TYPED"])

    def test_invoice(self):
        order = self._confirm_order("OC-500", client_order_ref="CLIENT-500")
        self._validate(order.picking_ids)
        invoice = order._create_invoices()
        self.assertEqual(invoice.purchase_order_number, "OC-500")
        self.assertEqual(self._references(invoice).mapped("origin_doc_number"), ["OC-500"])

    def test_grouped_invoice(self):
        orders = self._confirm_order("OC-501") | self._confirm_order("OC-502")
        for order in orders:
            self._validate(order.picking_ids)
        invoice = orders._create_invoices()
        self.assertEqual(len(invoice), 1)
        self.assertEqual(sorted(self._references(invoice).mapped("origin_doc_number")), ["OC-501", "OC-502"])

    def test_refund_gets_no_reference(self):
        self.product.invoice_policy = "order"
        order = self._confirm_order("OC-600")
        self.assertEqual(self._references(order._create_invoices()).mapped("origin_doc_number"), ["OC-600"])
        order.order_line.product_uom_qty = 1
        refund = order._create_invoices(final=True)
        self.assertEqual(refund.move_type, "out_refund")
        self.assertFalse(self._references(refund))
