##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSalePaymentOptions(TransactionCase):
    """A quotation of 1.000, a cash plan and a six installment plan with a 20% surcharge."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Its own company, so a localization installed in the base (taxes required per line,
        # for instance) does not decide whether these tests can create a line
        cls.company = cls.env["res.company"].create({"name": "Payment Options Co"})
        cls.env.user.company_ids = [Command.link(cls.company.id)]
        cls.env = cls.env(
            context={
                **cls.env.context,
                **DISABLED_MAIL_CONTEXT,
                "tracking_disable": True,
                "allowed_company_ids": [cls.company.id],
            }
        )
        cls.env.user.company_id = cls.company
        cls.card = cls.env["account.card"].create({"name": "Visa", "company_id": cls.company.id})
        cls.plan_cash = cls.env["account.card.installment"].create(
            {"name": "1", "card_id": cls.card.id, "divisor": 1, "surcharge_coefficient": 1.0}
        )
        cls.plan_six = cls.env["account.card.installment"].create(
            {"name": "6", "card_id": cls.card.id, "divisor": 6, "surcharge_coefficient": 1.2}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Payment Options Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Sofa", "type": "consu", "list_price": 1000.0, "taxes_id": [Command.clear()]}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "company_id": cls.company.id,
                "order_line": [Command.create({"product_id": cls.product.id, "product_uom_qty": 1})],
            }
        )

    def _option_values(self, plan, option_number=1, percentage=1.0):
        return {"card_installment_id": plan.id, "option_number": option_number, "percentage": percentage}

    def _create_template(self, name="Cash or six installments"):
        return self.env["sale.payment.option.template"].create(
            {
                "name": name,
                "payment_option_ids": [
                    Command.create(self._option_values(self.plan_cash, option_number=1)),
                    Command.create(self._option_values(self.plan_six, option_number=2)),
                ],
            }
        )

    def test_template_does_not_write_until_the_order_is_saved(self):
        """The bug: picking a template used to create the options in the database right away."""
        self.order.payment_option_ids = [Command.create(self._option_values(self.plan_cash))]
        template = self._create_template()
        options_before = self.env["sale.payment.option"].search_count([("sale_order_id", "=", self.order.id)])

        form = Form(self.order)
        form.payment_option_template_id = template
        self.assertEqual(len(form.payment_option_ids), 2, "the template options are loaded in the form")

        self.order.invalidate_recordset(["payment_option_ids"])
        self.assertEqual(
            self.env["sale.payment.option"].search_count([("sale_order_id", "=", self.order.id)]),
            options_before,
            "a discarded quotation keeps the options it had, and no leftovers from the template",
        )
        self.assertEqual(self.order.payment_option_ids.card_installment_id, self.plan_cash)

    def test_template_replaces_the_options_on_save(self):
        self.order.payment_option_ids = [Command.create(self._option_values(self.plan_cash))]
        template = self._create_template()

        with Form(self.order) as form:
            form.payment_option_template_id = template

        self.assertEqual(
            self.order.payment_option_ids.mapped("card_installment_id"),
            self.plan_cash | self.plan_six,
            "the saved options are the ones of the template, without repeats",
        )
        self.assertEqual(self.order.payment_option_ids.mapped("option_number"), [1, 2])

    def test_a_row_added_by_hand_is_its_own_option_at_100(self):
        with Form(self.order) as form:
            with form.payment_option_ids.new() as row:
                row.card_installment_id = self.plan_cash
            with form.payment_option_ids.new() as row:
                row.card_installment_id = self.plan_six

        self.assertEqual(len(self.order.payment_option_ids), 2, "one row added is one row saved")
        self.assertEqual(self.order.payment_option_ids.mapped("option_number"), [1, 2])
        self.assertEqual(self.order.payment_option_ids.mapped("percentage"), [1.0, 1.0])

    def test_an_option_that_does_not_add_up_to_100_cannot_be_saved(self):
        with self.assertRaises(ValidationError) as error:
            self.order.payment_option_ids = [
                Command.create(self._option_values(self.plan_cash, option_number=1, percentage=0.5))
            ]
        self.assertIn("Option 1", error.exception.args[0], "the message says which option is wrong")

    def test_deleting_part_of_an_option_leaves_it_under_100(self):
        self.order.payment_option_ids = [
            Command.create(self._option_values(self.plan_cash, option_number=1, percentage=0.5)),
            Command.create(self._option_values(self.plan_six, option_number=1, percentage=0.5)),
        ]
        deleted = self.order.payment_option_ids.filtered(lambda opt: opt.card_installment_id == self.plan_six)
        with self.assertRaises(ValidationError):
            self.order.write({"payment_option_ids": [Command.delete(deleted.id)]})

    def test_amounts_follow_the_order_total_before_saving(self):
        self.order.payment_option_ids = [Command.create(self._option_values(self.plan_six))]

        form = Form(self.order)
        with form.order_line.edit(0) as line:
            line.product_uom_qty = 2
        with form.payment_option_ids.edit(0) as row:
            # 2.000 with a 20% surcharge, in six installments
            self.assertAlmostEqual(row.amount_subtotal, 2400.0)
            self.assertAlmostEqual(row.amount_per_installment, 400.0)

    def test_the_surcharge_is_rounded(self):
        """The report prints the surcharge as it is: 1.04 must not reach it as 4.000000000000036."""
        plan = self.env["account.card.installment"].create(
            {"name": "3 with surcharge", "card_id": self.card.id, "divisor": 3, "surcharge_coefficient": 1.04}
        )
        option = self.env["sale.payment.option"].create({**self._option_values(plan), "sale_order_id": self.order.id})
        self.assertEqual(option.surcharge, 4.0)

    def test_an_option_can_combine_two_plans(self):
        self.order.payment_option_ids = [
            Command.create(self._option_values(self.plan_cash, option_number=1, percentage=0.5)),
            Command.create(self._option_values(self.plan_six, option_number=1, percentage=0.5)),
        ]
        options = self.order.payment_option_ids._grouped_by_option()

        self.assertEqual(len(options), 1, "both rows are the same option")
        self.assertAlmostEqual(sum(options[0].mapped("amount_subtotal")), 1100.0)

        # The printed breakdown keeps the two segments of the option together
        segments = self.order.order_line._get_payment_options_installments()
        self.assertEqual(len(segments), 1)
        self.assertEqual([segment["installment_qty"] for segment in segments[0]], [1, 6])
        self.assertAlmostEqual(segments[0][0]["amount_per_installment"], 500.0)
        self.assertAlmostEqual(segments[0][1]["amount_per_installment"], 100.0)

    def test_the_percentage_total_of_the_option_is_visible_in_the_list(self):
        self.order.payment_option_ids = [Command.create(self._option_values(self.plan_cash))]

        form = Form(self.order)
        with form.payment_option_ids.new() as row:
            row.card_installment_id = self.plan_six
            row.option_number = 1
            self.assertTrue(row.option_percentage_invalid, "option 1 now adds up to 200%")
            row.percentage = 0.5
        with form.payment_option_ids.edit(0) as row:
            row.percentage = 0.5
        with form.payment_option_ids.edit(1) as row:
            self.assertFalse(row.option_percentage_invalid, "option 1 adds up to 100% again")
