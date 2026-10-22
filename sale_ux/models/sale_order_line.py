##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    date_order = fields.Datetime("Order Date", related="order_id.date_order")

    team_id = fields.Many2one("crm.team", string="Sales Team", related="order_id.team_id")

    categ_id = fields.Many2one("product.category", string="Product Category", related="product_id.categ_id")

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

    @api.depends("order_id.force_invoiced_status")
    def _compute_invoice_status(self):
        """
        Sobreescribimos directamente el invoice status y no el qty_to_invoice
        ya que no nos importa tipo de producto y lo hace mas facil.
        Ademas no molesta dependencias con otros modulos que ya sobreescribian
        _get_to_invoice_qty
        """
        super()._compute_invoice_status()
        for line in self:
            # solo seteamos facturado si en sale o done
            if line.order_id.state not in ["sale", "done"]:
                continue
            if line.order_id.force_invoiced_status:
                line.invoice_status = line.order_id.force_invoiced_status

    def action_sale_history(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_ux.action_sale_order_line_usability_tree")
        action["domain"] = [("state", "in", ["sale", "done"]), ("product_id", "=", self.product_id.id)]
        action["display_name"] = _("Sale History for %s", self.product_id.display_name)
        action["context"] = {
            "search_default_order_partner_id": self.order_partner_id.parent_id.id or self.order_partner_id.id,
            "search_default_partner_id": 1,
        }
        return action

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if lines.filtered(lambda x: x.order_id and x.order_id.state == "done"):
            raise ValidationError(_("You cannot add lines to blocked sale orders."))
        return lines

    def _get_protected_fields(self):
        return super()._get_protected_fields() + ["discount"]

    def _compute_discount(self):
        if "discount1" in self._fields:
            return super()._compute_discount()
        lines = self.filtered(
            lambda x: x.order_id.state == "sale"
            and not (x.order_id.pricelist_id and x.pricelist_item_id._show_discount())
        )
        super(SaleOrderLine, self - lines)._compute_discount()

    def _compute_product_uom_id(self):
        """Override to respect only_packagings configuration"""
        for line in self:
            if line.product_id.product_tmpl_id.only_packagings and line.product_id.uom_ids:
                if line.product_uom_id and line.product_uom_id in line.product_id.uom_ids:
                    continue
                line.product_uom_id = line.product_id.uom_ids[0]
            else:
                super()._compute_product_uom_id()

    @api.depends("product_template_id.only_packagings")
    def _compute_allowed_uom_ids(self):
        lines = self.filtered(lambda x: x.product_id.product_tmpl_id.only_packagings)
        for line in lines:
            line.allowed_uom_ids = line.product_id.uom_ids
        super(SaleOrderLine, self - lines)._compute_allowed_uom_ids()

    def _get_product_catalog_lines_data(self, **kwargs):
        res = super()._get_product_catalog_lines_data(**kwargs)
        if (
            len(self) == 1
            and self.product_id.product_tmpl_id.only_packagings
            and self.product_uom_id in self.product_id.uom_ids
        ):
            res["uomDisplayName"] = self.product_uom_id.display_name
        return res

    def _get_downpayment_line_price_unit(self, invoices):
        """Core sums the down payment invoice lines without converting currencies.

        Needed when the down payment invoice currency differs from the order one
        (account_invoice_move_currency).
        """
        total = super()._get_downpayment_line_price_unit(invoices)
        for line in self.invoice_lines:
            if line.move_id.state != "posted" or line.move_id in invoices:
                continue
            if line.currency_id and self.currency_id and line.currency_id != self.currency_id:
                sign = 1 if line.move_id.move_type == "out_invoice" else -1
                converted_price_unit = line.currency_id._convert(
                    line.price_unit,
                    self.currency_id,
                    line.company_id,
                    line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(self),
                )
                total += sign * (converted_price_unit - line.price_unit)
        return total

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
        if not self.env["ir.config_parameter"].sudo().get_param("sale_ux.report_in_product_uom"):
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
