from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleLastSaleReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Last sale company", "is_company": True})
        cls.contact = cls.env["res.partner"].create(
            {"name": "Last sale contact", "parent_id": cls.partner.id, "type": "contact"}
        )
        cls.category = cls.env["product.category"].create({"name": "Last sale category"})
        cls.other_category = cls.env["product.category"].create({"name": "Last sale other category"})
        cls.product = cls.env["product.product"].create(
            {"name": "Last sale product", "categ_id": cls.category.id, "list_price": 10.0}
        )
        cls.other_product = cls.env["product.product"].create(
            {"name": "Last sale other product", "categ_id": cls.other_category.id, "list_price": 20.0}
        )

    def _create_order(self, product, days_ago, partner=None, state="sale", company=None):
        orders = self.env["sale.order"].sudo()
        values = {
            "partner_id": (partner or self.partner).id,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1})],
        }
        if company:
            orders = orders.with_company(company)
            values["company_id"] = company.id
        # Con sale_exception (y sus módulos de reglas: partner no aprobado, límite de crédito) instalado, confirmar
        # puede devolver el asistente de excepciones en vez de confirmar. Lo que se prueba acá es otra cosa.
        if "ignore_exception" in orders._fields:
            values["ignore_exception"] = True
        order = orders.create(values)
        if state in ("sale", "cancel"):
            order.action_confirm()
        if state == "cancel":
            order._action_cancel()
        order.date_order = fields.Datetime.now() - timedelta(days=days_ago, hours=1)
        return order

    def _rows(self, product=None):
        self.env.flush_all()
        domain = [("partner_id", "=", self.partner.id)]
        if product:
            domain.append(("product_id", "=", product.id))
        return self.env["sale.last.sale.report"].sudo().search(domain)

    def test_only_confirmed_orders_are_counted(self):
        self._create_order(self.product, 3, state="draft")
        self._create_order(self.product, 4, state="cancel")
        self.assertFalse(self._rows(self.product))
        self._create_order(self.product, 5)
        self.assertEqual(len(self._rows(self.product)), 1)

    def test_last_sale_is_the_most_recent_order_of_the_product(self):
        self._create_order(self.product, 20)
        recent = self._create_order(self.product, 5)
        rows = self._rows(self.product)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.date_order, recent.date_order.date())
        self.assertEqual(rows.days_since, 5)

    def test_one_row_per_product_with_its_category(self):
        self._create_order(self.product, 10)
        self._create_order(self.other_product, 2)
        rows = self._rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows.filtered(lambda r: r.product_id == self.product).product_category_id, self.category)
        self.assertEqual(
            rows.filtered(lambda r: r.product_id == self.other_product).product_category_id, self.other_category
        )
        self.assertEqual(rows.filtered(lambda r: r.product_id == self.other_product).days_since, 2)

    def test_orders_of_a_contact_are_grouped_under_the_commercial_partner(self):
        self._create_order(self.product, 7, partner=self.contact)
        rows = self._rows(self.product)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.partner_id, self.partner)
        self.assertEqual(rows.days_since, 7)

    def test_company_and_contact_orders_share_the_same_row(self):
        self._create_order(self.product, 30)
        self._create_order(self.product, 6, partner=self.contact)
        rows = self._rows(self.product)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.days_since, 6)

    def _create_user(self, login, groups, companies=None):
        companies = companies or self.env.company
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "company_id": companies[0].id,
                    "company_ids": [Command.set(companies.ids)],
                    "group_ids": [Command.set([self.env.ref(xmlid).id for xmlid in groups])],
                }
            )
        )

    def test_salesman_can_read_the_report_and_cannot_write_it(self):
        self._create_order(self.product, 5)
        salesman = self._create_user("last_sale_salesman", ["base.group_user", "sales_team.group_sale_salesman"])
        rows = self.env["sale.last.sale.report"].with_user(salesman).search([("partner_id", "=", self.partner.id)])
        self.assertTrue(rows)
        with self.assertRaises(AccessError):
            rows[:1].with_user(salesman).write({"days_since": 99})

    def test_internal_user_without_sales_group_cannot_read_the_report(self):
        user = self._create_user("last_sale_internal", ["base.group_user"])
        with self.assertRaises(AccessError):
            self.env["sale.last.sale.report"].with_user(user).search([])

    def _sales_groups(self):
        return ["base.group_user", "sales_team.group_sale_salesman"]

    def test_salesman_only_sees_the_sales_of_their_company(self):
        other_company = self.env["res.company"].create({"name": "Last sale other company"})
        own = self._create_order(self.product, 5)
        other = self._create_order(self.product, 9, company=other_company)
        self.env.flush_all()
        domain = [("partner_id", "=", self.partner.id)]
        self.assertEqual(
            self.env["sale.last.sale.report"].sudo().search(domain).company_id, own.company_id | other.company_id
        )
        salesman = self._create_user("last_sale_company_salesman", self._sales_groups())
        rows = self.env["sale.last.sale.report"].with_user(salesman).search(domain)
        self.assertEqual(rows.company_id, own.company_id)
        self.assertEqual(rows.days_since, 5)

    def test_salesman_of_two_companies_sees_the_active_ones(self):
        other_company = self.env["res.company"].create({"name": "Last sale second company"})
        self._create_order(self.product, 5)
        self._create_order(self.product, 9, company=other_company)
        self.env.flush_all()
        both = self.env.company | other_company
        salesman = self._create_user("last_sale_two_company_salesman", self._sales_groups(), companies=both)
        domain = [("partner_id", "=", self.partner.id)]
        report = self.env["sale.last.sale.report"].with_user(salesman)
        self.assertEqual(report.with_context(allowed_company_ids=both.ids).search(domain).company_id, both)
        self.assertEqual(
            report.with_context(allowed_company_ids=other_company.ids).search(domain).company_id, other_company
        )
