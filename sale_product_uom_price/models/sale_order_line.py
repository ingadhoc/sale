##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.tools import float_round

PRICE_IN_PRODUCT_UOM_PARAM = "sale_product_uom_price.report_in_product_uom"
SKIP_ROUNDING_CONTEXT = "skip_price_unit_product_uom_rounding"


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    price_unit_product_uom = fields.Float(
        string="Price per Product Unit",
        compute="_compute_price_unit_product_uom",
        readonly=False,
        # Same as purchase.order.line.price_unit_product_uom in core: only the decimals the value
        # has are shown, which priced per product unit are those of any other price
        min_display_digits="Product Price",
        help="Unit price in the unit of the product, for instance per kg on a line sold by "
        "packaging, with the same tax criteria as the printed quotation. If you change it, the "
        "unit price of the line is recomputed.",
    )
    price_unit_product_uom_editable = fields.Boolean(compute="_compute_price_unit_product_uom")

    @api.model
    def _price_in_product_uom(self):
        """Whether lines sold in another unit are priced per product unit."""
        return bool(self.env["ir.config_parameter"].sudo().get_param(PRICE_IN_PRODUCT_UOM_PARAM))

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
        """Decimals of the price per product unit.

        Priced per product unit, that price is the one agreed with the customer and needs no more
        decimals than any other price. Otherwise it comes from a conversion that rarely divides
        evenly, and the extra decimals are what makes quantity x unit price match the subtotal.
        """
        price_digits = self.env["decimal.precision"].precision_get("Product Price")
        return price_digits if self._price_in_product_uom() else max(price_digits, 4)

    def _get_product_uom_price(self, product_uom):
        """Price of the line per product unit, with the tax criteria of the printed document."""
        self.ensure_one()
        return float_round(
            self.product_uom_id._compute_price(self._get_report_price_unit(), product_uom),
            precision_digits=self._get_product_uom_price_digits(),
        )

    def _get_price_unit_from_product_uom_price(self, product_uom_price, product_uom):
        """Unit price of the line, in the unit of the line, for a price per product unit."""
        self.ensure_one()
        report_price = product_uom._compute_price(product_uom_price, self.product_uom_id)
        price_unit = self._get_price_unit_from_report_price(report_price)
        if self._price_in_product_uom():
            # Rounding here is what would bring the extra decimals back
            return price_unit
        return float_round(price_unit, precision_digits=self.env["decimal.precision"].precision_get("Product Price"))

    def _rounded_price_unit(self):
        """Unit price of the line brought onto a whole price per product unit, so the price and
        the quantity of the printed document multiply into the subtotal. The unit price as it is
        when the line is not priced per product unit.
        """
        self.ensure_one()
        product_uom = self._price_in_product_uom() and self._get_report_product_uom()
        if not product_uom:
            return self.price_unit
        return self._get_price_unit_from_product_uom_price(self._get_product_uom_price(product_uom), product_uom)

    def _round_price_unit_product_uom(self):
        """Apply the rounding to prices that did not come from the pricelist, such as an imported
        order or a price written over the API."""
        for line in self:
            price_unit = line._rounded_price_unit()
            if price_unit == line.price_unit:
                continue
            vals = {"price_unit": price_unit}
            currency = line.currency_id or line.company_id.currency_id or self.env.company.currency_id
            if not currency.compare_amounts(line.technical_price_unit, line.price_unit):
                # A price of the pricelist stays one: core tells a manual price apart by comparing
                # the two, and goes on recomputing the line only while they agree
                vals["technical_price_unit"] = price_unit
            line.with_context(**{SKIP_ROUNDING_CONTEXT: True}).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._round_price_unit_product_uom()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get(SKIP_ROUNDING_CONTEXT) and (
            {"price_unit", "product_id", "product_uom_id"} & vals.keys()
        ):
            self._round_price_unit_product_uom()
        return res

    def _reset_price_unit(self):
        """The price of the pricelist is rounded per product unit before it reaches the line: the
        rule rounds the price of the packaging, and the division to the product unit undoes it."""
        super()._reset_price_unit()
        price_unit = self._rounded_price_unit()
        if price_unit != self.price_unit:
            # technical_price_unit too, so the price goes on being one of the pricelist for core
            self.update({"price_unit": price_unit, "technical_price_unit": price_unit})

    @api.depends("price_unit", "product_uom_id", "product_id.uom_id", "qty_invoiced")
    def _compute_price_unit_product_uom(self):
        for line in self:
            product_uom = line._get_report_product_uom()
            # A price of zero is a valid price, so what tells the column apart is the UoM
            line.price_unit_product_uom_editable = bool(product_uom) and line.qty_invoiced <= 0
            line.price_unit_product_uom = line._get_product_uom_price(product_uom) if product_uom else 0.0

    @api.onchange("price_unit_product_uom")
    def _onchange_price_unit_product_uom(self):
        """Onchange and not inverse: the field is not stored, so an inverse would only run on
        save and the salesperson would not see the new unit price."""
        for line in self:
            product_uom = line._get_report_product_uom()
            if not product_uom:
                continue
            # technical_price_unit is left alone, so the line keeps a manual price
            line.price_unit = line._get_price_unit_from_product_uom_price(line.price_unit_product_uom, product_uom)

    @api.onchange("price_unit")
    def _onchange_price_unit(self):
        """So a price typed by hand lands on the rounding while the salesperson is on the line."""
        for line in self:
            line.price_unit = line._rounded_price_unit()

    def _get_report_product_uom_values(self):
        """Quantity and unit price in the product UoM for customer documents.

        Only when the setting is enabled and the line is sold in another UoM of the same
        reference (e.g. a packaging). Returns False otherwise.
        """
        self.ensure_one()
        if not self._price_in_product_uom():
            return False
        product_uom = self._get_report_product_uom()
        if not product_uom:
            return False
        return {
            "qty": self.product_uom_id._compute_quantity(self.product_uom_qty, product_uom, round=False),
            "uom": product_uom,
            "price_unit": self._get_product_uom_price(product_uom),
            "price_options": {"widget": "float", "decimal_precision": "Product Price"},
        }
