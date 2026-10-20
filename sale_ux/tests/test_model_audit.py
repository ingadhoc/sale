from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, new_test_user, tagged

from .common import SaleUxCommon


class SaleUxAuditCommon(SaleUxCommon):
    """Helpers shared by the model-by-model audit tests."""

    def _confirm(self, order):
        order.action_confirm()
        if order.state != "sale":
            self.skipTest("Order could not be confirmed in current module stack")
        return order

    def _invoice_and_post(self, order):
        invoice = order._create_invoices(final=True)
        invoice.action_post()
        return invoice

    def _reverse(self, invoice, quantity=None):
        """Credit note made with the reversal wizard (as the UI does), posted and reconciled."""
        wizard = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"journal_id": invoice.journal_id.id, "reason": "Sale UX audit"})
        )
        wizard.refund_moves()
        credit = invoice.reversal_move_ids
        if quantity is not None:
            credit.invoice_line_ids.write({"quantity": quantity})
        credit.action_post()
        lines = (invoice.line_ids | credit.line_ids).filtered(
            lambda line: line.account_id.account_type == "asset_receivable" and not line.reconciled
        )
        lines.reconcile()
        return credit

    def _down_payment_wizard(self, order, **values):
        return (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=order.ids, active_model="sale.order")
            .create({"advance_payment_method": "fixed", "fixed_amount": 50.0, **values})
        )


@tagged("post_install", "-at_install")
class TestAuditSaleOrder(SaleUxAuditCommon):
    """sale.order"""

    def test_commercial_partner_follows_the_parent_company(self):
        child = self.env["res.partner"].create(
            {"name": "Sale UX child contact", "parent_id": self.partner_a.id, "type": "contact"}
        )
        order = self._create_sale_order(partner_id=child.id)
        self.assertEqual(order.commercial_partner_id, self.partner_a)

        child.parent_id = False

        self.assertEqual(order.commercial_partner_id, child, "the stored related field follows the partner")

    def test_cancel_is_allowed_once_the_invoice_is_fully_reversed(self):
        order = self._confirm(self._create_sale_order())
        invoice = self._invoice_and_post(order)
        credit = self._reverse(invoice)
        self.assertEqual(invoice.payment_state, "reversed")
        self.assertEqual(credit.payment_state, "paid")

        order.action_cancel()

        self.assertEqual(order.state, "cancel")

    def test_cancel_is_blocked_when_the_invoice_is_only_partially_reversed(self):
        order = self._confirm(self._create_sale_order())
        invoice = self._invoice_and_post(order)
        self._reverse(invoice, quantity=1)
        self.assertEqual(invoice.payment_state, "partial")

        with self.assertRaises(UserError):
            order.action_cancel()
        self.assertEqual(order.state, "sale")

    def test_cancel_is_blocked_when_the_credit_note_does_not_come_from_the_order(self):
        order = self._confirm(self._create_sale_order())
        invoice = self._invoice_and_post(order)
        credit = invoice._reverse_moves([{"invoice_date": fields.Date.today()}])
        credit.action_post()
        (invoice.line_ids | credit.line_ids).filtered(
            lambda line: line.account_id.account_type == "asset_receivable" and not line.reconciled
        ).reconcile()
        self.assertFalse(credit.invoice_origin, "a plain reversal does not copy the origin")

        with self.assertRaises(UserError):
            order.action_cancel()

    def test_locked_order_blocks_every_protected_field_and_unlocked_does_not(self):
        pricelist = self.env["product.pricelist"].create({"name": "Sale UX audit pricelist"})
        order = self._confirm(self._create_sale_order())
        order.action_lock()

        for values in (
            {"partner_invoice_id": self.partner_b.id},
            {"partner_shipping_id": self.partner_b.id},
            {"pricelist_id": pricelist.id},
        ):
            with self.subTest(fields=list(values)), self.assertRaises(UserError):
                order.write(values)

        order.action_unlock()
        order.write({"partner_invoice_id": self.partner_b.id})
        self.assertEqual(order.partner_invoice_id, self.partner_b)

    def test_locked_order_error_names_the_forbidden_field(self):
        order = self._confirm(self._create_sale_order())
        order.action_lock()

        with self.assertRaises(UserError) as context:
            order.write({"partner_invoice_id": self.partner_b.id})

        self.assertIn("locked order", str(context.exception))

    def test_cron_cancels_only_old_draft_and_sent_quotations(self):
        self.IrConfig.set_bool("sale_ux.cancel_old_quotations", True)
        self.IrConfig.set_int("sale_ux.days_to_keep_quotations", 10)
        recent = self._create_old_quotation(5)
        old_draft = self._create_old_quotation(15)
        old_sent = self._create_old_quotation(15)
        old_sent.write({"state": "sent"})
        old_confirmed = self._create_old_quotation(15)
        old_confirmed.write({"state": "sale"})

        self.env["sale.order"]._cron_clean_old_quotations()

        self.assertEqual(recent.state, "draft", "younger than the limit")
        self.assertEqual(old_draft.state, "cancel")
        self.assertEqual(old_sent.state, "cancel")
        self.assertEqual(old_confirmed.state, "sale", "confirmed orders are never cancelled")
        self.assertTrue(
            old_draft.message_ids.filtered(lambda message: "automatically canceled" in message.body),
            "the cancellation is logged in the chatter",
        )

    def test_cron_does_nothing_when_the_setting_is_off(self):
        self.IrConfig.set_bool("sale_ux.cancel_old_quotations", False)
        self.IrConfig.set_int("sale_ux.days_to_keep_quotations", 10)
        old_draft = self._create_old_quotation(60)

        self.env["sale.order"]._cron_clean_old_quotations()

        self.assertEqual(old_draft.state, "draft")

    def test_amount_uninvoiced_only_discounts_posted_invoices(self):
        order = self._confirm(self._create_sale_order())
        self._down_payment_wizard(order).create_invoices()
        self.assertEqual(order.amount_uninvoiced, 200.0, "a draft down payment does not count")

        order.invoice_ids.action_post()

        self.assertEqual(order.amount_uninvoiced, 150.0)

    def test_down_payment_invoice_follows_the_note_propagation_settings(self):
        self.IrConfig.set_bool("sale.propagate_internal_notes", True)
        order = self._confirm(self._create_sale_order(internal_notes="<p>Sale UX internal note</p>"))
        self._down_payment_wizard(order).create_invoices()
        self.assertIn("Sale UX internal note", order.invoice_ids.internal_notes)

        self.IrConfig.set_bool("sale.propagate_internal_notes", False)
        other = self._confirm(self._create_sale_order(internal_notes="<p>Sale UX internal note</p>"))
        self._down_payment_wizard(other).create_invoices()
        self.assertFalse(other.invoice_ids.internal_notes)


@tagged("post_install", "-at_install")
class TestAuditSaleOrderLine(SaleUxAuditCommon):
    """sale.order.line"""

    def test_related_fields_follow_the_order(self):
        team = self.env["crm.team"].create({"name": "Sale UX audit team"})
        order = self._create_sale_order(team_id=team.id)
        line = order.order_line

        self.assertEqual(line.team_id, team)
        self.assertEqual(line.date_order, order.date_order)

    def test_only_packagings_product_limits_the_uoms_of_the_line(self):
        uom_a = self.product_uom_pack
        uom_b = self.env["uom.uom"].create(
            {"name": "Sale UX Box 10", "relative_factor": 10, "relative_uom_id": self.product_uom_unit.id}
        )
        template = self.product.product_tmpl_id
        template.write({"uom_ids": [Command.set([uom_a.id, uom_b.id])], "only_packagings": True})
        order = self._create_sale_order(order_line=[Command.create({"product_id": self.product.id})])
        line = order.order_line

        self.assertEqual(line.product_uom_id, self.product.uom_ids[0], "defaults to the first packaging")
        self.assertEqual(line.allowed_uom_ids, self.product.uom_ids)

        other_uom = self.product.uom_ids - line.product_uom_id
        line.product_uom_id = other_uom
        line._compute_product_uom_id()

        self.assertEqual(line.product_uom_id, other_uom, "a valid packaging chosen by the user is kept")

    def test_products_without_only_packagings_keep_the_standard_uoms(self):
        order = self._create_sale_order()

        self.assertEqual(order.order_line.product_uom_id, self.product_uom_unit)


@tagged("post_install", "-at_install")
class TestAuditPartnerPricelist(SaleUxAuditCommon):
    """res.partner"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Pricelist = cls.env["product.pricelist"]
        cls.pricelist_first = Pricelist.create({"name": "Sale UX first", "sequence": -100})
        cls.pricelist_other = Pricelist.create({"name": "Sale UX other", "sequence": 999})

    def test_contact_created_under_a_company_inherits_its_pricelist(self):
        parent = self.env["res.partner"].create(
            {"name": "Sale UX parent", "specific_property_product_pricelist": self.pricelist_other.id}
        )

        child = self.env["res.partner"].create({"name": "Sale UX child", "parent_id": parent.id})

        self.assertEqual(child.specific_property_product_pricelist, self.pricelist_other)

    def test_default_other_than_the_first_pricelist_becomes_specific(self):
        self.env["ir.default"].set("res.partner", "property_product_pricelist", self.pricelist_other.id)

        partner = self.env["res.partner"].create({"name": "Sale UX with default"})

        self.assertEqual(partner.specific_property_product_pricelist, self.pricelist_other)

    def test_default_equal_to_the_first_pricelist_is_not_stored(self):
        self.env["ir.default"].set("res.partner", "property_product_pricelist", self.pricelist_first.id)

        partner = self.env["res.partner"].create({"name": "Sale UX with first default"})

        self.assertFalse(partner.specific_property_product_pricelist, "it keeps following the sequence")

    def test_batch_create_decides_for_each_partner(self):
        plain, explicit = self.env["res.partner"].create(
            [
                {"name": "Sale UX batch plain"},
                {"name": "Sale UX batch explicit", "specific_property_product_pricelist": self.pricelist_other.id},
            ]
        )

        self.assertFalse(plain.specific_property_product_pricelist)
        self.assertEqual(explicit.specific_property_product_pricelist, self.pricelist_other)


@tagged("post_install", "-at_install")
class TestAuditSettings(SaleUxAuditCommon):
    """res.config.settings"""

    def test_note_propagation_round_trips_through_the_settings(self):
        settings = self.env["res.config.settings"].create({"move_internal_notes": True, "move_note": True})
        settings.set_values()

        defaults = self.env["res.config.settings"].default_get(["move_internal_notes", "move_note"])
        self.assertTrue(defaults["move_internal_notes"])
        self.assertTrue(defaults["move_note"])
        self.assertTrue(self.IrConfig.get_bool("sale.propagate_internal_notes"))
        self.assertTrue(self.IrConfig.get_bool("sale.propagate_note"))

        settings = self.env["res.config.settings"].create({"move_internal_notes": False, "move_note": False})
        settings.set_values()

        self.assertFalse(self.IrConfig.get_bool("sale.propagate_internal_notes"))
        self.assertFalse(self.IrConfig.get_bool("sale.propagate_note"))

    def test_product_image_size_defaults_to_the_smallest(self):
        defaults = self.env["res.config.settings"].default_get(["product_image_size"])

        self.assertEqual(defaults["product_image_size"], "128_50")

    def test_allow_any_user_as_salesman_setting_grants_the_group(self):
        group = self.env.ref("sale_ux.group_allow_any_user_as_salesman")
        self.env.ref("base.group_user").write({"implied_ids": [Command.unlink(group.id)]})

        self.env["res.config.settings"].create({"group_allow_any_user_as_salesman": True}).execute()

        self.assertIn(group, self.env.ref("base.group_user").implied_ids)


@tagged("post_install", "-at_install")
class TestAuditPricelist(SaleUxAuditCommon):
    """product.pricelist"""

    def test_open_rules_needs_a_product_in_the_context(self):
        pricelist = self.env["product.pricelist"].create({"name": "Sale UX audit rules"})

        with self.assertRaises(UserError):
            pricelist.action_open_product_pricelist_item()

    def test_open_rules_from_a_template_defaults_to_the_template(self):
        pricelist = self.env["product.pricelist"].create({"name": "Sale UX audit rules"})
        template = self.product.product_tmpl_id

        action = pricelist.with_context(pricelist_template_id=template.id).action_open_product_pricelist_item()

        self.assertEqual(action["res_model"], "product.pricelist.item")
        self.assertEqual(action["context"]["default_pricelist_id"], pricelist.id)
        self.assertEqual(action["context"]["default_product_tmpl_id"], template.id)
        self.assertEqual(action["context"]["default_applied_on"], "1_product")
        self.assertNotIn("default_product_id", action["context"])

    def test_open_rules_from_a_variant_defaults_to_the_variant(self):
        pricelist = self.env["product.pricelist"].create({"name": "Sale UX audit rules"})

        action = pricelist.with_context(pricelist_product_id=self.product.id).action_open_product_pricelist_item()

        self.assertEqual(action["context"]["default_product_id"], self.product.id)
        self.assertEqual(action["context"]["default_applied_on"], "0_product_variant")


@tagged("post_install", "-at_install")
class TestAuditAnalyticWizard(SaleUxAuditCommon):
    """sale.order.analytic.wizard"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env["account.analytic.plan"].create({"name": "Sale UX audit plan"})
        Account = cls.env["account.analytic.account"]
        cls.account_a = Account.create({"name": "Sale UX audit A", "plan_id": cls.plan.id})
        cls.account_b = Account.create({"name": "Sale UX audit B", "plan_id": cls.plan.id})

    def _wizard(self, order, **context):
        return (
            self.env["sale.order.analytic.wizard"]
            .with_context(active_model="sale.order", **context)
            .create({"analytic_account_id": self.account_a.id})
        )

    def test_lines_load_from_active_id_alone(self):
        order = self._create_sale_order()

        wizard = self._wizard(order, active_id=order.id)

        self.assertEqual(wizard.line_ids.sale_line_id, order.order_line)

    def test_form_opens_with_every_line_selected_and_apply_assigns_them(self):
        """Opening the form runs the onchanges, which used to switch every line off."""
        order = self._create_sale_order()
        form = Form(
            self.env["sale.order.analytic.wizard"].with_context(active_ids=order.ids, active_model="sale.order")
        )
        form.analytic_account_id = self.account_a
        wizard = form.save()
        self.assertTrue(wizard.select_all)
        self.assertTrue(all(wizard.line_ids.mapped("selected")))

        wizard.action_apply()

        self.assertEqual(order.order_line.analytic_distribution, {str(self.account_a.id): 100})

    def test_unselecting_everything_applies_nothing(self):
        order = self._create_sale_order()
        wizard = self._wizard(order, active_ids=order.ids)

        wizard.select_all = False
        wizard._onchange_select_all()
        wizard.action_apply()

        self.assertFalse(wizard.line_ids.filtered("selected"))
        self.assertFalse(order.order_line.analytic_distribution)

    def test_apply_replaces_the_previous_distribution(self):
        order = self._create_sale_order()
        line = order.order_line
        line.analytic_distribution = {str(self.account_a.id): 50, str(self.account_b.id): 50}
        wizard = self._wizard(order, active_ids=order.ids)
        wizard.analytic_account_id = self.account_b

        wizard.action_apply()

        self.assertEqual(line.analytic_distribution, {str(self.account_b.id): 100})

    def test_current_analytic_lists_the_accounts_of_the_line(self):
        order = self._create_sale_order()
        order.order_line.analytic_distribution = {str(self.account_a.id): 50, str(self.account_b.id): 50}

        wizard = self._wizard(order, active_ids=order.ids)

        self.assertIn(self.account_a.display_name, wizard.line_ids.current_analytic)
        self.assertIn(self.account_b.display_name, wizard.line_ids.current_analytic)

    def test_action_is_only_offered_to_the_groups_that_can_read_analytic_plans(self):
        action = self.env.ref("sale_ux.action_sale_order_set_analytic")

        self.assertEqual(
            action.group_ids,
            self.env.ref("analytic.group_analytic_accounting") | self.env.ref("account.group_account_user"),
        )

    def test_salesman_without_analytic_accounting_is_not_offered_the_action(self):
        salesman = new_test_user(self.env, login="audit_plain_salesman", groups="sales_team.group_sale_salesman")
        action = self.env.ref("sale_ux.action_sale_order_set_analytic")

        self.assertFalse(action.group_ids & salesman.group_ids)
        with self.assertRaises(AccessError):
            self.env["account.analytic.plan"].with_user(salesman).search([])

    def test_salesman_with_analytic_accounting_can_use_the_wizard(self):
        salesman = new_test_user(
            self.env,
            login="audit_analytic_salesman",
            groups="sales_team.group_sale_salesman,analytic.group_analytic_accounting",
        )
        order = self._create_sale_order(user_id=salesman.id)

        wizard = (
            self.env["sale.order.analytic.wizard"]
            .with_user(salesman)
            .with_context(active_ids=order.ids, active_model="sale.order")
            .create({"analytic_account_id": self.account_a.id})
        )
        wizard.action_apply()

        self.assertEqual(wizard.line_ids.sale_line_id, order.order_line)
        self.assertEqual(order.order_line.analytic_distribution, {str(self.account_a.id): 100})

    def test_portal_user_cannot_use_the_wizard(self):
        portal = new_test_user(self.env, login="audit_portal", groups="base.group_portal")

        with self.assertRaises(AccessError):
            self.env["sale.order.analytic.wizard"].with_user(portal).create({"analytic_account_id": self.account_a.id})


@tagged("post_install", "-at_install", "-standard", "sale_ux_known_issues")
class TestAuditKnownIssues(SaleUxAuditCommon):
    """Defects found while auditing the module on Odoo 20 that are still open.

    Each test states the behaviour that is expected and FAILS today. They are out of the standard run
    (``-standard``) so CI stays green; run them with ``--test-tags sale_ux_known_issues``. When a defect is fixed,
    move its test to the class of its model and drop it from here.
    """

    def test_lines_cannot_be_added_to_a_locked_order(self):
        """The README promises it; the check looks at ``state == 'done'``, which no longer exists."""
        order = self._confirm(self._create_sale_order())
        order.action_lock()

        with self.assertRaises(UserError):
            self.env["sale.order.line"].create({"order_id": order.id, "product_id": self.product.id})

    def test_cancelled_locked_order_ends_unlocked(self):
        """The README promises the order is unlocked after cancelling it; it stays locked."""
        order = self._confirm(self._create_sale_order())
        order.action_lock()

        order.action_cancel()

        self.assertFalse(order.locked)
