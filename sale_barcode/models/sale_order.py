##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, models


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "barcodes.barcode_events_mixin"]

    def on_barcode_scanned(self, barcode):
        # Skip system commands (let barcode_handlers.js handle them)
        if barcode.startswith(("OCD", "OBT")):
            return

        # Handle products only
        product = self.env["product.product"].search([("barcode", "=", barcode)], limit=1)
        if product:
            self._add_product(product)
        elif packaging := self._get_packaging_from_barcode(barcode):
            self._add_product(packaging.product_id, uom=packaging.uom_id)
        else:
            return {
                "warning": {
                    "title": _("Wrong barcode"),
                    "message": _('The barcode "%(barcode)s" doesn\'t' " correspond to a proper product.")
                    % {"barcode": barcode},
                }
            }

    def _get_packaging_from_barcode(self, barcode):
        """Barcodes are unique across products and packagings, so a barcode that
        matches no product may still be one of a product packaging."""
        return self.env["product.uom"].search([("barcode", "=", barcode)], limit=1)

    def _add_product(self, product, qty=1.0, uom=None):
        uom = uom or product.uom_id
        if uom not in product.product_tmpl_id._get_available_uoms():
            # the packaging is not sellable for this product, fall back to its unit
            qty = uom._compute_quantity(qty, product.uom_id)
            uom = product.uom_id
        corresponding_line = self.order_line.filtered(lambda x: x.product_id == product)
        if corresponding_line:
            # If multiple lines exist, increment the first one
            line = corresponding_line[0]
            line.product_uom_qty += self._get_scanned_qty(line, qty, uom)
        else:
            self.order_line.new(
                {
                    "product_id": product.id,
                    "product_uom_id": uom.id,
                    "product_uom_qty": qty,
                    "order_id": self.id,
                }
            )
        return True

    def _get_scanned_qty(self, line, qty, uom):
        """Quantity to add to an existing line, expressed in the unit of that line.

        Scanning the packaging of a product sold by unit adds its whole content,
        and scanning a unit of a product sold by packaging adds a whole packaging
        instead of a fraction of one.
        """
        line_uom = line.product_uom_id
        if line_uom == uom:
            return qty
        line_qty = uom._compute_quantity(qty, line_uom, round=False)
        return 1.0 if line_uom.compare(line_qty, 1.0) < 0 else line_qty
