##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import SaleOrderTypeUxCommon


@tagged("post_install", "-at_install")
class TestSaleOrderTypeUx(SaleOrderTypeUxCommon):
    def test_invoices_are_split_by_order_type(self):
        """Invoicing orders of different types gives one invoice per type.

        Two orders of the same customer and company would be grouped into a
        single invoice by the core; the module splits them by type unless the
        caller asks for grouping. Covers the override of _create_invoices,
        whose signature changed in 20.0.
        """
        order_a = self._create_order(self.type_a)
        order_b = self._create_order(self.type_b)
        orders = order_a | order_b
        orders.action_confirm()

        invoices = orders._create_invoices()

        self.assertEqual(len(invoices), 2)
        self.assertEqual(invoices.sale_type_id, self.type_a | self.type_b)
        self.assert_invoices_keep_their_type(orders, invoices)

    def test_single_type_is_not_split(self):
        """Orders sharing their type are still grouped into one invoice.

        Control: the split must happen because the types differ, not every time
        several orders are invoiced together.
        """
        orders = self._create_order(self.type_a) | self._create_order(self.type_a)
        orders.action_confirm()

        with self.subTest("dos pedidos del mismo tipo dan una sola factura"):
            invoices = orders._create_invoices()
            self.assertEqual(len(invoices), 1)
            self.assert_invoices_keep_their_type(orders, invoices)

        with self.subTest("pedir una factura por pedido sigue llegando al core"):
            invoices.unlink()
            per_order_invoices = orders._create_invoices(grouped=True)
            self.assertEqual(len(per_order_invoices), 2)
            self.assert_invoices_keep_their_type(orders, per_order_invoices)

    def test_invoice_is_prepared_for_the_invoice_company_of_the_type(self):
        """The invoice is prepared in the invoice company set on the type."""
        self.type_a.invoice_company_id = self.other_company
        order = self._create_order(self.type_a)

        values = order._prepare_invoice()

        self.assertEqual(values["company_id"], self.other_company.id)

    def test_journal_of_another_company_is_rejected(self):
        """A journal outside the invoice company of the type is rejected.

        Positive control: the constraint has to block, otherwise a type could
        invoice through a journal of a company that is not the one invoicing.
        """
        with self.assertRaises(ValidationError):
            self.type_a.write(
                {
                    "invoice_company_id": self.other_company.id,
                    "journal_id": self.sale_journal.id,
                }
            )

    def test_order_takes_fiscal_position_and_team_from_the_type(self):
        """The type wins over what the customer would give to the order."""
        self.type_a.write(
            {
                "fiscal_position_id": self.fiscal_position.id,
                "team_id": self.sales_team.id,
            }
        )

        with self.subTest("la posición fiscal del tipo gana"):
            order = self._create_order(self.type_a)
            self.assertEqual(order.fiscal_position_id, self.fiscal_position)

        with self.subTest("el equipo del tipo entra al cambiar el tipo"):
            order = self._create_order(self.type_b)
            order.type_id = self.type_a
            order._onchange_team_id()
            self.assertEqual(order.team_id, self.sales_team)
