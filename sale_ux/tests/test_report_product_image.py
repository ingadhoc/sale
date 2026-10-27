##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import re

from odoo import Command
from odoo.tests import TransactionCase, tagged

# 1x1 png
IMAGE = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


@tagged("post_install", "-at_install")
class TestReportProductImage(TransactionCase):
    """La imagen del producto viaja embebida en el reporte, no como enlace.

    Con un enlace a /web/image el PDF se arma con la sesion de quien lo pide, y un
    usuario de portal no puede leer los productos que no estan publicados en el sitio
    web: la regla de website_sale se lo bloquea y la foto sale vacia.
    """

    def _render_image_cell(self, order):
        html = self.env["ir.actions.report"]._render_qweb_html("sale.report_saleorder", order.ids)[0]
        cell = re.search(rb'<td[^>]*name="td_image".*?</td>', html, re.S)
        self.assertTrue(cell, "El reporte no trae la columna de imagen")
        return cell.group(0).decode()

    def test_product_image_is_embedded(self):
        self.env["ir.config_parameter"].sudo().set_param("sale_ux.show_product_image_on_report", "True")
        product = self.env["product.product"].create({"name": "Report image", "image_1920": IMAGE})
        self.assertTrue(product.image_sale_order)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Report image customer"}).id,
                "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1})],
            }
        )

        cell = self._render_image_cell(order)

        self.assertIn("data:image", cell)
        self.assertNotIn("/web/image", cell)
