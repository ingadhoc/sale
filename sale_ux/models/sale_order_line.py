##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    date_order = fields.Datetime("Order Date", related="order_id.date_order")

    team_id = fields.Many2one("crm.team", string="Sales Team", related="order_id.team_id")

    categ_id = fields.Many2one("product.category", string="Product Category", related="product_id.categ_id")

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

    def _get_report_price_unit(self):
        """Unit price shown on customer documents, in the line UoM. Hook for localizations."""
        self.ensure_one()
        return self.price_unit

    def _get_report_product_uom_values(self):
        """Quantity and unit price in the product UoM for customer documents.

        Only when the setting is enabled and the line is sold in another UoM of the same
        reference (e.g. a packaging). Returns False otherwise.
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
            or not self.env["ir.config_parameter"].sudo().get_param("sale_ux.report_in_product_uom")
        ):
            return False
        price_digits = self.env["decimal.precision"].precision_get("Product Price")
        return {
            "qty": line_uom._compute_quantity(self.product_uom_qty, product_uom, round=False),
            "uom": product_uom,
            "price_unit": line_uom._compute_price(self._get_report_price_unit(), product_uom),
            # Extra decimals so that quantity x unit price matches the subtotal
            "price_options": {
                "widget": "float",
                "precision": max(price_digits, 4),
                "min_precision": price_digits,
            },
        }
