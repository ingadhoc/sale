from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user, tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestSaleOrder(SaleUxCommon):
    def _prepare_order_for_invoicing(self, order, policy="order"):
        """Normalize test preconditions across minimal and full-stack module sets."""
        if "restrict_sales" in self.env.company._fields:
            self.env.company.restrict_sales = "amount_depends"
            if "restrict_sales_amount" in self.env.company._fields:
                self.env.company.restrict_sales_amount = 10**9
        commercial_partner = order.partner_id.commercial_partner_id
        if "partner_state" in commercial_partner._fields:
            commercial_partner.partner_state = "approved"
        if "type_id" in order._fields and order.type_id and "invoice_policy" in order.type_id._fields:
            order.type_id.invoice_policy = policy
        if order.state not in ("sale", "done"):
            order.action_confirm()
        if order.state not in ("sale", "done"):
            self.skipTest("Order could not be confirmed in current module stack")
        return order

    def test_prepare_invoice_respects_note_propagation_settings(self):
        self.env.company.invoice_terms = "Company invoice terms"
        self.IrConfig.set_param("account.use_invoice_terms", "True")
        self.IrConfig.set_param("sale.propagate_internal_notes", "True")
        self.IrConfig.set_param("sale.propagate_note", "False")
        order = self._create_sale_order(
            internal_notes="<p>Internal note</p>",
            note="Sale note",
        )

        vals = order._prepare_invoice()

        self.assertEqual(vals["internal_notes"], "<p>Internal note</p>")
        self.assertIn("Company invoice terms", str(vals["narration"]))

        self.IrConfig.set_param("sale.propagate_note", "True")
        vals = order._prepare_invoice()

        self.assertIn("Sale note", str(vals["narration"]))

    def test_get_invoiceable_lines_can_remove_note_lines(self):
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 1.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                ),
                Command.create(
                    {
                        "display_type": "line_note",
                        "name": "Internal invoice note",
                    }
                ),
            ]
        )
        order.action_confirm()
        note_line = order.order_line.filtered(lambda line: line.display_type == "line_note")

        self.IrConfig.set_param("sale_ux.dont_send_notes_to_invoices", "True")
        invoiceable_lines = order._get_invoiceable_lines()

        self.assertNotIn(note_line, invoiceable_lines)

    def test_get_update_prices_lines_honors_context_exclusions(self):
        order = self._create_sale_order(
            order_line=[
                Command.create({"product_id": self.product.id, "price_unit": 100.0}),
                Command.create({"product_id": self.product.id, "price_unit": 200.0}),
            ]
        )
        excluded_line = order.order_line[0]

        lines = order.with_context(lines_to_not_update_ids=excluded_line.ids)._get_update_prices_lines()

        self.assertNotIn(excluded_line, lines)
        self.assertIn(order.order_line[1], lines)

    def test_locked_order_blocks_protected_fields(self):
        order = self._create_sale_order()
        order.action_confirm()
        order.action_lock()

        with self.assertRaises(UserError):
            order.write({"partner_id": self.partner_b.id})

        order.write({"client_order_ref": "Allowed reference"})
        self.assertEqual(order.client_order_ref, "Allowed reference")

    def test_locked_order_can_be_cancelled(self):
        order = self._create_sale_order()
        order.action_confirm()
        order.action_lock()

        order.action_cancel()

        self.assertEqual(order.state, "cancel")

    def test_force_invoiced_status_requires_system_user(self):
        order = self._create_sale_order()
        self._prepare_order_for_invoicing(order)
        sale_user = new_test_user(
            self.env,
            login="sale_ux_user",
            groups="sales_team.group_sale_salesman",
        )
        order.user_id = sale_user

        with self.assertRaises(ValidationError):
            order.with_user(sale_user).force_invoiced_status = "invoiced"

        order.force_invoiced_status = "invoiced"
        order.order_line._compute_invoice_status()
        order._compute_amount_to_invoice()

        self.assertEqual(order.order_line.invoice_status, "invoiced")
        self.assertEqual(order.amount_to_invoice, 0.0)

    def test_amount_uninvoiced_is_total_for_confirmed_uninvoiced_order(self):
        order = self._create_sale_order()
        self._prepare_order_for_invoicing(order)

        order._compute_amount_uninvoiced()

        self.assertEqual(order.amount_uninvoiced, order.amount_total)

    def test_amount_uninvoiced_is_zero_for_draft_order(self):
        order = self._create_sale_order()

        order._compute_amount_uninvoiced()

        self.assertEqual(order.amount_uninvoiced, 0.0)

    def test_prepare_analytic_account_without_company(self):
        self.IrConfig.set_param("sale_ux.analytic_account_without_company", "True")
        order = self._create_sale_order(client_order_ref="REF-001")

        values = order._prepare_analytic_account_data(prefix="Project")

        self.assertEqual(values["name"], f"Project: {order.name}")
        self.assertEqual(values["code"], "REF-001")
        self.assertFalse(values["company_id"])
        self.assertEqual(values["partner_id"], order.partner_id.id)

        values = order._prepare_analytic_account_data()

        self.assertEqual(values["name"], order.name)

    def test_cron_clean_old_quotations_cancels_expired_drafts(self):
        self.IrConfig.set_param("sale_ux.cancel_old_quotations", "True")
        self.IrConfig.set_param("sale_ux.days_to_keep_quotations", "10")
        old_order = self._create_old_quotation(days_old=20)
        recent_order = self._create_old_quotation(days_old=2)

        self.env["sale.order"]._cron_clean_old_quotations()

        self.assertEqual(old_order.state, "cancel")
        self.assertEqual(recent_order.state, "draft")

    def test_action_preview_sale_order_opens_new_tab(self):
        order = self._create_sale_order()

        action = order.action_preview_sale_order()

        self.assertEqual(action["target"], "new")

    def test_onchange_pricelist_can_recompute_prices_automatically(self):
        self.IrConfig.set_param("sale_ux.update_prices_automatically", "True")
        order = self._create_sale_order()

        order._onchange_pricelist_id_show_update_prices()

        self.assertTrue(order.order_line)

    def test_onchange_fiscal_position_recomputes_line_taxes(self):
        order = self._create_sale_order()

        order._onchange_fiscal_position_id()

        self.assertTrue(order.order_line)

    def test_action_update_prices_ignores_empty_recordset(self):
        result = self.env["sale.order"].action_update_prices()

        self.assertIsNone(result)

    def test_copy_removes_inactive_taxes_from_new_order(self):
        tax = self.tax_sale_a.copy({"name": "Sale UX inactive tax"})
        order = self._create_sale_order()
        order.order_line.tax_ids = tax
        tax.active = False

        copied_order = order.copy()

        self.assertFalse(copied_order.order_line.tax_ids.filtered(lambda tax: not tax.active))

    def test_create_invoices_creates_refund_when_amount_is_zero(self):
        """Test that invoices with zero total and negative quantities are created as refunds"""
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": -2.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )
        self._prepare_order_for_invoicing(order)

        invoices = order._create_invoices(final=True)

        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices.move_type, "out_refund")
        self.assertEqual(invoices.amount_total, 200.0)

    def test_action_cancel_blocks_when_related_invoices_exist(self):
        """Test that cancelling SO is blocked when related invoices exist in non-draft/non-cancel state"""
        order = self._create_sale_order()
        self._prepare_order_for_invoicing(order)
        invoice = order._create_invoices(final=True)[0]
        invoice.action_post()

        with self.assertRaises(UserError):
            order.action_cancel()

    def test_action_cancel_allows_when_invoices_are_draft(self):
        """Test that cancelling SO is allowed when invoices are in draft state"""
        order = self._create_sale_order()
        self._prepare_order_for_invoicing(order)
        order._create_invoices(final=True)

        order.action_cancel()

        self.assertEqual(order.state, "cancel")

    def test_copy_logs_duplication_message(self):
        """Test that copying a SO logs a message with origin reference"""
        order = self._create_sale_order()

        copied_order = order.copy()

        messages = copied_order.message_ids.filtered(lambda msg: "duplicated from" in msg.body.lower())
        self.assertTrue(messages)
        self.assertIn(order.name, messages[0].body)

    def test_action_confirm_multiple_sales_from_list(self):
        """Test confirming multiple sales orders from list view"""
        if not hasattr(self.env["sale.order"], "action_confirm_sale_order"):
            self.skipTest("action_confirm_sale_order is provided by an optional dependency")

        order_1 = self._create_sale_order()
        order_2 = self._create_sale_order()
        orders = order_1 | order_2

        result = orders.action_confirm_sale_order()

        self.assertEqual(order_1.state, "sale")
        self.assertEqual(order_2.state, "sale")
        self.assertIsNotNone(result)

    def _mass_cancel(self, orders):
        return self.env["sale.mass.cancel.orders"].with_context(active_ids=orders.ids).create({}).action_mass_cancel()

    def test_mass_cancel_blocks_when_related_invoices_exist(self):
        """Test that the mass cancel wizard is blocked when related invoices exist"""
        order = self._create_sale_order()
        self._prepare_order_for_invoicing(order)
        invoice = order._create_invoices(final=True)[0]
        invoice.action_post()

        with self.assertRaises(UserError):
            self._mass_cancel(order)

        self.assertEqual(order.state, "sale")

    def test_mass_cancel_allows_when_invoices_are_draft(self):
        """Test that the mass cancel wizard cancels orders with draft invoices only"""
        order = self._create_sale_order()
        self._prepare_order_for_invoicing(order)
        order._create_invoices(final=True)

        self._mass_cancel(order)

        self.assertEqual(order.state, "cancel")

    def test_mass_cancel_error_names_the_blocking_order(self):
        """Test that the mass cancel error identifies the order blocking the batch"""
        order = self._create_sale_order()
        self._prepare_order_for_invoicing(order)
        invoice = order._create_invoices(final=True)[0]
        invoice.action_post()

        with self.assertRaises(UserError) as catcher:
            self._mass_cancel(order)

        self.assertIn(order.display_name, str(catcher.exception))

    def test_mass_cancel_skips_already_cancelled_orders(self):
        """Test that an order cancelled by the old path does not block the batch"""
        blocking_order = self._create_sale_order()
        self._prepare_order_for_invoicing(blocking_order)
        invoice = blocking_order._create_invoices(final=True)[0]
        invoice.action_post()
        # the standard wizard used to cancel these without running any check
        blocking_order._action_cancel()
        self.assertEqual(blocking_order.state, "cancel")
        quotation = self._create_sale_order()

        self._mass_cancel(blocking_order | quotation)

        self.assertEqual(quotation.state, "cancel")

    def test_action_cancel_on_several_orders_names_every_blocking_one(self):
        """Test that cancelling a recordset reports each order whose invoices block it"""
        orders = self.env["sale.order"]
        for _index in range(2):
            order = self._create_sale_order()
            self._prepare_order_for_invoicing(order)
            invoice = order._create_invoices(final=True)[0]
            invoice.action_post()
            orders |= order

        with self.assertRaises(UserError) as catcher:
            orders.action_cancel()

        for order in orders:
            self.assertIn(order.display_name, str(catcher.exception))
        self.assertEqual(set(orders.mapped("state")), {"sale"})

    def test_mass_cancel_cancels_several_quotations(self):
        """Test that the mass cancel wizard still cancels a whole recordset"""
        orders = self._create_sale_order() | self._create_sale_order()

        self._mass_cancel(orders)

        self.assertEqual(set(orders.mapped("state")), {"cancel"})
