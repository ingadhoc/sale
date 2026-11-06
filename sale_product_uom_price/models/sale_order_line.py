##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.tools import float_round


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    price_unit_product_uom = fields.Float(
        string="Price per Product Unit",
        compute="_compute_price_unit_product_uom",
        readonly=False,
        # Same as purchase.order.line.price_unit_product_uom in core: the value is not rounded,
        # so the extra decimals the conversion needs are kept and only shown when there are any
        min_display_digits="Product Price",
        help="Unit price in the unit of the product, for instance per kg on a line sold by "
        "packaging, with the same tax criteria as the printed quotation. If you change it, the "
        "unit price of the line is recomputed.",
    )
    price_unit_product_uom_editable = fields.Boolean(compute="_compute_price_unit_product_uom")

    def _get_report_price_unit(self, price=None):
        """Unit price shown on customer documents, in the line UoM. Hook for localizations;
        `price` evaluates it on a price other than the one of the line."""
        self.ensure_one()
        return self.price_unit if price is None else price

    def _get_price_unit_from_report_price(self, report_price):
        """Inverse of _get_report_price_unit, both in the line UoM.

        The report price is affine on the unit price, whatever the taxes do with it, so two
        probes are enough and a localization only has to implement the direct hook.
        """
        self.ensure_one()
        base = self._get_report_price_unit(price=0.0)
        slope = self._get_report_price_unit(price=1.0) - base
        if not slope:
            return report_price
        return (report_price - base) / slope

    def _get_report_product_uom(self):
        """Product UoM when the line is sold in another UoM of the same reference (e.g. a
        packaging), so prices can also be expressed per product unit. False otherwise.
        """
        self.ensure_one()
        product_uom = self.product_id.uom_id
        line_uom = self.product_uom_id
        if (
            self.display_type
            or not product_uom
            or not line_uom
            or line_uom == product_uom
            or not line_uom._has_common_reference(product_uom)
        ):
            return False
        return product_uom

    @api.model
    def _get_product_uom_price_digits(self):
        """Extra decimals so that quantity x unit price matches the subtotal."""
        return max(self.env["decimal.precision"].precision_get("Product Price"), 4)

    @api.depends("price_unit", "product_uom_id", "product_id.uom_id", "qty_invoiced")
    def _compute_price_unit_product_uom(self):
        digits = self._get_product_uom_price_digits()
        for line in self:
            product_uom = line._get_report_product_uom()
            # A price of zero is a valid price, so what tells the column apart is the UoM
            line.price_unit_product_uom_editable = bool(product_uom) and line.qty_invoiced <= 0
            line.price_unit_product_uom = (
                float_round(
                    line.product_uom_id._compute_price(line._get_report_price_unit(), product_uom),
                    precision_digits=digits,
                )
                if product_uom
                else 0.0
            )

    @api.onchange("price_unit_product_uom")
    def _onchange_price_unit_product_uom(self):
        """Onchange and not inverse: the field is not stored, so an inverse would only run on
        save and the salesperson would not see the new unit price."""
        price_digits = self.env["decimal.precision"].precision_get("Product Price")
        for line in self:
            product_uom = line._get_report_product_uom()
            if not product_uom:
                continue
            report_price = product_uom._compute_price(line.price_unit_product_uom, line.product_uom_id)
            # The unit price rules, so it is rounded first and the column follows it.
            # technical_price_unit is left alone, so the line keeps a manual price
            line.price_unit = float_round(
                line._get_price_unit_from_report_price(report_price), precision_digits=price_digits
            )

    def _get_report_product_uom_values(self):
        """Quantity and unit price in the product UoM for customer documents.

        Only when the setting is enabled and the line is sold in another UoM of the same
        reference (e.g. a packaging). Returns False otherwise.
        """
        self.ensure_one()
        param = "sale_product_uom_price.report_in_product_uom"
        if not self.env["ir.config_parameter"].sudo().get_param(param):
            return False
        product_uom = self._get_report_product_uom()
        if not product_uom:
            return False
        price_digits = self.env["decimal.precision"].precision_get("Product Price")
        return {
            "qty": self.product_uom_id._compute_quantity(self.product_uom_qty, product_uom, round=False),
            "uom": product_uom,
            "price_unit": self.product_uom_id._compute_price(self._get_report_price_unit(), product_uom),
            "price_options": {
                "widget": "float",
                "precision": self._get_product_uom_price_digits(),
                "min_precision": price_digits,
            },
        }
