from lxml import html as lxml_html
from odoo import Command
from odoo.tests import tagged

from .common import SaleUxCommon


@tagged("post_install", "-at_install")
class TestLineNumbers(SaleUxCommon):
    """With the company setting "Line Numbers" on, Odoo 20 numbers the sections and the notes too. In 19
    only the lines without `display_type` had a number, and that is what `sale_ux` keeps."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.show_sol_numbers = True
        cls.order = cls._create_sale_order(
            order_line=[
                Command.create({"display_type": "line_section", "name": "Section 1", "sequence": 10}),
                Command.create({"product_id": cls.product.id, "product_uom_qty": 1.0, "sequence": 20}),
                Command.create({"display_type": "line_note", "name": "A note", "sequence": 30}),
                Command.create({"display_type": "line_subsection", "name": "Subsection 1", "sequence": 40}),
                Command.create({"product_id": cls.product.id, "product_uom_qty": 2.0, "sequence": 50}),
                Command.create({"display_type": "line_section", "name": "Section 2", "sequence": 60}),
                Command.create({"product_id": cls.product.id, "product_uom_qty": 3.0, "sequence": 70}),
            ]
        )

    def _cells(self, html, name):
        tree = lxml_html.fromstring(html)
        return [cell.text_content().strip() for cell in tree.xpath("//td[@name='%s']" % name)]

    def _assert_numbered_cells(self, html):
        self.assertEqual(self._cells(html, "td_product_line_no"), ["1", "2", "3"])
        # the cell is kept, so the columns stay aligned, but it has no number
        self.assertEqual(self._cells(html, "td_section_line_no"), ["", "", ""])
        self.assertEqual(self._cells(html, "td_note_line_no"), [""])

    def test_offset_does_not_count_sections_subsections_and_notes(self):
        lines = self.order.order_line.sorted("sequence")

        offsets = {line.sequence: line.line_number_offset for line in lines}

        # the offset of a row is how many numbered lines come before it
        self.assertEqual(offsets, {10: 0, 20: 0, 30: 1, 40: 1, 50: 1, 60: 2, 70: 2})

    def test_offset_is_zero_when_the_company_does_not_number_the_lines(self):
        self.env.company.show_sol_numbers = False
        self.order.order_line.invalidate_recordset(["line_number_offset"])

        self.assertEqual(set(self.order.order_line.mapped("line_number_offset")), {0})

    def test_offset_of_a_single_line_counts_the_whole_order(self):
        last_line = self.order.order_line.sorted("sequence")[-1]

        self.assertEqual(last_line.line_number_offset, 2)

    def test_offset_does_not_count_the_lines_inside_a_collapsed_section(self):
        last_line = self.order.order_line.filtered(lambda line: line.sequence == 70)
        subsection = self.order.order_line.filtered(lambda line: line.name == "Subsection 1")
        section = self.order.order_line.filtered(lambda line: line.name == "Section 1")

        # the product of the subsection is hidden by it, so it does not take a number
        subsection.collapse_composition = True
        self.order.order_line.invalidate_recordset(["line_number_offset"])
        self.assertEqual(last_line.line_number_offset, 1)

        # every product of Section 1 is hidden by it
        subsection.collapse_composition = False
        section.collapse_composition = True
        self.order.order_line.invalidate_recordset(["line_number_offset"])
        self.assertEqual(last_line.line_number_offset, 0)

    def test_quotation_report_numbers_only_the_lines(self):
        html = (
            self.env["ir.actions.report"]._render_qweb_html("sale.action_report_saleorder", self.order.ids)[0].decode()
        )

        self._assert_numbered_cells(html)

    def test_portal_numbers_only_the_lines(self):
        html = str(
            self.env["ir.qweb"]._render(
                "sale.sale_order_portal_content",
                {
                    "sale_order": self.order,
                    "report_type": "html",
                    "resize_to_attachment": False,
                    "backend_url": "",
                    "res_company": self.order.company_id,
                    "user": self.env.user,
                },
            )
        )

        self._assert_numbered_cells(html)

    def test_report_has_no_number_column_when_the_company_does_not_number_the_lines(self):
        self.env.company.show_sol_numbers = False

        html = (
            self.env["ir.actions.report"]._render_qweb_html("sale.action_report_saleorder", self.order.ids)[0].decode()
        )

        self.assertFalse(self._cells(html, "td_product_line_no"))
