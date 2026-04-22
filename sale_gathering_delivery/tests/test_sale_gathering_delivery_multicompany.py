from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleGatheringDeliveryMulticompany(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # company_a = already provided by AccountTestInvoicingCommon as cls.env.company
        cls.company_a = cls.env.company

        # Create a second, fully-configured company via the helper
        cls.company_data_2 = cls.setup_other_company(name="IAS Events")
        cls.company_b = cls.company_data_2["company"]

        cls.env.user.company_ids = [(4, cls.company_a.id), (4, cls.company_b.id)]

        # Taxes - use the ones already set up per company
        cls.tax_a = cls.company_data["default_tax_sale"]
        cls.tax_b = cls.company_data_2["default_tax_sale"]

        # Make tax_b's group name match tax_a's so the wizard can map them
        if cls.tax_a and cls.tax_b:
            cls.tax_b.tax_group_id.name = cls.tax_a.tax_group_id.name
            cls.tax_b.amount = cls.tax_a.amount
            cls.tax_b.type_tax_use = cls.tax_a.type_tax_use
            cls.tax_b.price_include_override = cls.tax_a.price_include_override

        # Journal for company_b
        cls.journal_b = cls.company_data_2["default_journal_sale"]

        # Products
        cls.product_delivery = cls.env["product.product"].create(
            {
                "name": "Delivery_007 Envío estándar",
                "type": "service",
                "taxes_id": [(6, 0, [cls.tax_a.id])] if cls.tax_a else [],
            }
        )
        cls.product_delivery.with_company(cls.company_a).property_account_income_id = cls.company_data[
            "default_account_revenue"
        ]

        cls.product_gathering = cls.env["product.product"].create(
            {
                "name": "COM02 Caja de almacenamiento",
                "type": "consu",
            }
        )
        cls.product_gathering.with_company(cls.company_a).property_account_income_id = cls.company_data[
            "default_account_revenue"
        ]

    def _create_gathering_order(self, sale_type=False):
        order_values = {
            "partner_id": self.partner_a.id,
            "company_id": self.company_a.id,
            "is_gathering": True,
        }
        if "type_id" in self.env["sale.order"]._fields:
            order_values["type_id"] = False
        if sale_type:
            order_values["type_id"] = sale_type.id
        so = self.env["sale.order"].with_company(self.company_a).create(order_values)

        self.env["sale.order.line"].create(
            {
                "order_id": so.id,
                "product_id": self.product_gathering.id,
                "product_uom_qty": 1.0,
                "price_unit": 15.80,
                "tax_id": [(6, 0, [self.tax_a.id])] if self.tax_a else [],
            }
        )
        self.env["sale.order.line"].create(
            {
                "order_id": so.id,
                "product_id": self.product_delivery.id,
                "product_uom_qty": 1.0,
                "price_unit": 10.00,
                "is_delivery": True,
                "tax_id": [(6, 0, [self.tax_a.id])] if self.tax_a else [],
            }
        )

        so.action_confirm()
        return so

    def test_change_company_advance_invoice(self):
        """
        Verifies that changing the company on a gathering advance invoice with a
        delivery line does NOT raise an error (Incompatible Companies).
        Without our fix in account_move_line.py this raises:
            UserError: Incompatible companies on records:
                - "(Acopio) Delivery_007 Envío estándar" belongs to company "IAS Events"
                  and tax belongs to "Muebleria ARG".
        """
        so = self._create_gathering_order()

        # Create Advance Invoice (gathering wizard)
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=[so.id], active_model="sale.order")
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 15.80,
                }
            )
        )
        invoice = wizard._create_invoices(so)

        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.company_id, self.company_a)
        self.assertTrue(
            any(line.product_id == self.product_delivery for line in invoice.invoice_line_ids),
            "Invoice should contain the delivery line",
        )

        # Change company using the account_multicompany_ux wizard.
        # Skip if the module is not installed (e.g. CI running only sale_gathering_delivery).
        # Without our fix in account_move_line.py this raises UserError.
        if "account.change.company" not in self.env:
            self.skipTest("account_multicompany_ux not installed")
        change_wizard = (
            self.env["account.change.company"]
            .with_context(active_id=invoice.id)
            .create(
                {
                    "company_id": self.company_b.id,
                    "journal_id": self.journal_b.id,
                }
            )
        )
        change_wizard.change_company()  # must NOT raise

        # Post-change assertions
        self.assertEqual(invoice.company_id, self.company_b, "Invoice company should be company_b")
        for line in invoice.invoice_line_ids:
            for tax in line.tax_ids:
                self.assertEqual(
                    tax.company_id,
                    self.company_b,
                    f"Tax '{tax.name}' still belongs to '{tax.company_id.name}', expected '{self.company_b.name}'",
                )

    def test_delivery_line_created_after_invoice_company_change(self):
        """
        When sale_order_type_ux changes the advance invoice company before
        sale_gathering_delivery appends the delivery line, the delivery line
        taxes must already belong to the invoice company at create time.
        """
        if "type_id" not in self.env["sale.order"]._fields:
            self.skipTest("sale_order_type not installed")
        if "account.change.company" not in self.env:
            self.skipTest("account_multicompany_ux not installed")
        if self.env["sale.order.type"]._fields["journal_id"].check_company:
            self.skipTest("sale_order_type_ux not installed")

        sale_type = self.env["sale.order.type"].create(
            {
                "name": "Cross Company Gathering",
                "company_id": self.company_a.id,
                "journal_id": self.journal_b.id,
            }
        )
        so = self._create_gathering_order(sale_type=sale_type)

        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=[so.id], active_model="sale.order")
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 15.80,
                }
            )
        )
        invoice = wizard._create_invoices(so)

        self.assertEqual(invoice.company_id, self.company_b, "Invoice company should be company_b")
        delivery_invoice_line = invoice.invoice_line_ids.filtered(lambda line: line.product_id == self.product_delivery)
        self.assertTrue(delivery_invoice_line, "Invoice should contain the delivery line")
        for tax in delivery_invoice_line.tax_ids:
            self.assertEqual(tax.company_id, self.company_b)
