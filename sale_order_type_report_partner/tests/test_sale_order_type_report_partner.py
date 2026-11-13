##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import base64

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import BinaryBytes

# two 1x1 pngs, enough to tell one image apart from the other in the html
BRAND_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
COMPANY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@tagged("post_install", "-at_install")
class TestSaleOrderTypeReportPartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.partner_id.write({"name": "Legal Entity SA", "image_1920": BinaryBytes(COMPANY_PNG)})
        cls.brand_partner = cls.env["res.partner"].create(
            {
                "name": "Second Brand",
                "street": "Brand Street 123",
                "image_1920": BinaryBytes(BRAND_PNG),
            }
        )
        cls.company_logo_b64 = cls.company.logo.to_base64()
        cls.brand_logo_b64 = cls.brand_partner.image_1920.to_base64()
        cls.customer = cls.env["res.partner"].create({"name": "SOT Report Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "SOT Report Product", "type": "consu", "list_price": 100.0}
        )
        cls.type_with_partner = cls.env["sale.order.type"].create(
            {"name": "Brand Type", "report_partner_id": cls.brand_partner.id}
        )
        cls.type_without_partner = cls.env["sale.order.type"].create({"name": "Plain Type"})

    def _create_order(self, order_type):
        return self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "type_id": order_type.id,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )

    def _render(self, order):
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html("sale.report_saleorder", order.ids)
        return html.decode()

    def test_header_uses_the_report_partner(self):
        """The order type partner replaces the company data on the header."""
        html = self._render(self._create_order(self.type_with_partner))

        self.assertIn("Second Brand", html)
        self.assertIn("Brand Street 123", html)
        self.assertIn(self.brand_logo_b64, html)
        self.assertNotIn(self.company_logo_b64, html)

    def test_header_falls_back_to_the_company(self):
        """Without a report partner the header is the native one."""
        html = self._render(self._create_order(self.type_without_partner))

        self.assertIn("Legal Entity SA", html)
        self.assertIn(self.company_logo_b64, html)
        self.assertNotIn("Second Brand", html)
        self.assertNotIn(self.brand_logo_b64, html)
