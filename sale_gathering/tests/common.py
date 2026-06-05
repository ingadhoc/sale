from odoo import Command
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.tests.common import TransactionCase


class SaleGatheringCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context={
                **cls.env.context,
                **DISABLED_MAIL_CONTEXT,
                "tracking_disable": True,
            }
        )
        code_suffix = str(sum(ord(char) for char in cls.__name__))

        cls.receivable_account = cls.env["account.account"].create(
            {
                "name": "Sale Gathering Test Receivable",
                "code": f"SGRE{code_suffix}",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.payable_account = cls.env["account.account"].create(
            {
                "name": "Sale Gathering Test Payable",
                "code": f"SGPA{code_suffix}",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Sale Gathering Test Income",
                "code": f"SGIN{code_suffix}",
                "account_type": "income",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "name": "Sale Gathering Test Expense",
                "code": f"SGEX{code_suffix}",
                "account_type": "expense",
            }
        )

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Sale Gathering Customer",
                "property_account_receivable_id": cls.receivable_account.id,
                "property_account_payable_id": cls.payable_account.id,
            }
        )

        cls.product_a = cls.env["product.product"].create(
            {
                "name": "Sale Gathering Product A",
                "type": "consu",
                "invoice_policy": "order",
                "list_price": 100.0,
                "standard_price": 50.0,
                "property_account_income_id": cls.income_account.id,
                "property_account_expense_id": cls.expense_account.id,
                "taxes_id": [Command.clear()],
                "supplier_taxes_id": [Command.clear()],
            }
        )
        cls.product_b = cls.env["product.product"].create(
            {
                "name": "Sale Gathering Product B",
                "type": "consu",
                "invoice_policy": "order",
                "list_price": 120.0,
                "standard_price": 70.0,
                "property_account_income_id": cls.income_account.id,
                "property_account_expense_id": cls.expense_account.id,
                "taxes_id": [Command.clear()],
                "supplier_taxes_id": [Command.clear()],
            }
        )

        sale_exception_installed = cls.env["sale.order"]._fields.get("ignore_exception")
        if sale_exception_installed:
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})

    @classmethod
    def _create_order(cls, *, is_gathering=True, lines=None, **values):
        order_values = {
            "partner_id": cls.partner.id,
            "is_gathering": is_gathering,
            "order_line": lines
            or [
                Command.create(
                    {
                        "product_id": cls.product_a.id,
                        "product_uom_qty": 2.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ],
        }
        order_values.update(values)
        return cls.env["sale.order"].create(order_values)

    @classmethod
    def _confirm_gathering_order(cls, **values):
        order = cls._create_order(is_gathering=True, **values)
        order.action_confirm()
        return order

    def _create_advance_payment_wizard(self, order, *, amount=100.0):
        return (
            self.env["sale.advance.payment.inv"]
            .with_context(
                active_model="sale.order",
                active_ids=order.ids,
            )
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": amount,
                }
            )
        )

    def _create_invoice_gathering_zero_wizard(self, order):
        return (
            self.env["sale.advance.payment.inv"]
            .with_context(
                active_model="sale.order",
                active_ids=order.ids,
            )
            .create(
                {
                    "advance_payment_method": "invoice_gathering_zero",
                }
            )
        )

    def _post_invoice(self, invoice):
        if invoice.state == "draft":
            invoice.action_post()
        return invoice

    def _register_payment(self, invoice):
        payment_wizard = (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=invoice.ids,
            )
            .create(
                {
                    "journal_id": self.env["account.journal"]
                    .search(
                        [
                            ("type", "in", ["bank", "cash"]),
                            ("company_id", "=", invoice.company_id.id),
                        ],
                        limit=1,
                    )
                    .id,
                }
            )
        )
        payment_wizard.action_create_payments()
        return invoice

    def _create_and_pay_gathering_downpayment(self, order, *, amount=250.0):
        wizard = self._create_advance_payment_wizard(order, amount=amount)
        wizard.create_invoices()
        invoice = order.invoice_ids.filtered(lambda move: move.state != "cancel").sorted("id")[-1]
        self._post_invoice(invoice)
        self._register_payment(invoice)
        return invoice
