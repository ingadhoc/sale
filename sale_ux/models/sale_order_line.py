##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    date_order = fields.Datetime("Order Date", related="order_id.date_order")

    team_id = fields.Many2one("crm.team", string="Sales Team", related="order_id.team_id")

    categ_id = fields.Many2one("product.category", string="Product Category", related="product_id.categ_id")

    is_sold = fields.Boolean(
        string="Sold",
        default=True,
        copy=False,
        help="Uncheck to record that the customer did not buy this line. The whole quantity moves to "
        "'Unsold Quantity' and the line is neither delivered nor invoiced.",
    )

    lost_qty = fields.Float(
        string="Unsold Quantity",
        digits="Product Unit of Measure",
        copy=False,
        help="Quantity quoted to the customer but not sold, in the unit of measure of the line.",
    )

    lost_reason_id = fields.Many2one(
        "sale.order.line.lost.reason",
        string="Unsold Reason",
        ondelete="restrict",
        copy=False,
    )

    lost_amount = fields.Monetary(
        string="Unsold Amount",
        compute="_compute_lost_amount",
        store=True,
        currency_field="currency_id",
    )

    lost_qty_enabled = fields.Boolean(compute="_compute_lost_qty_enabled")

    def _compute_lost_qty_enabled(self):
        # only here to switch view elements: "groups" cannot express an AND of two groups
        self.lost_qty_enabled = self.env.user.has_group("sale_ux.group_lost_qty")

    @api.depends("lost_qty", "price_unit", "discount")
    def _compute_lost_amount(self):
        for line in self:
            line.lost_amount = line.price_unit * line.lost_qty * (1 - (line.discount or 0.0) / 100.0)

    @api.constrains("lost_qty", "lost_reason_id")
    def _check_lost_reason(self):
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        for line in self:
            if float_compare(line.lost_qty, 0.0, precision_digits=precision) > 0 and not line.lost_reason_id:
                raise ValidationError(
                    _('You must set an unsold reason for line "%s", which has an unsold quantity.', line.name)
                )

    def _balance_lost_qty_vals(self, vals):
        """Keep the quoted total (ordered + unsold) when one of the two sides is written.

        The onchange below does this for the form; this does it for every other path
        (the editable list, an import, the API), where no onchange runs.
        """
        self.ensure_one()
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        line_vals = dict(vals)
        quoted_qty = self.product_uom_qty + self.lost_qty
        if "lost_qty" in vals:
            line_vals["product_uom_qty"] = max(quoted_qty - vals["lost_qty"], 0.0)
            if float_is_zero(vals["lost_qty"], precision_digits=precision):
                line_vals.setdefault("lost_reason_id", False)
            line_vals["is_sold"] = not float_is_zero(line_vals["product_uom_qty"], precision_digits=precision)
        elif vals["is_sold"]:
            line_vals["product_uom_qty"] = quoted_qty
            line_vals["lost_qty"] = 0.0
            line_vals.setdefault("lost_reason_id", False)
        else:
            line_vals["lost_qty"] = quoted_qty
            line_vals["product_uom_qty"] = 0.0
        return line_vals

    def write(self, vals):
        balance = ("is_sold" in vals or "lost_qty" in vals) and not self.env.context.get("skip_lost_qty_balance")
        if not balance:
            return super().write(vals)
        for line in self:
            super(SaleOrderLine, line).write(line._balance_lost_qty_vals(vals))
        return True

    @api.onchange("is_sold")
    def _onchange_is_sold(self):
        """Move the whole quantity to (or back from) the unsold column."""
        for line in self:
            if line.is_sold:
                line.product_uom_qty += line.lost_qty
                line.lost_qty = 0.0
                line.lost_reason_id = False
            else:
                line.lost_qty += line.product_uom_qty
                line.product_uom_qty = 0.0

    @api.onchange("lost_qty")
    def _onchange_lost_qty(self):
        """A partial loss is taken out of the ordered quantity, which never goes negative.

        The quoted total (ordered + unsold) is taken from the saved line so that editing the
        unsold quantity several times before saving keeps giving the same result.
        """
        precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        for line in self:
            quoted_qty = line._origin.product_uom_qty + line._origin.lost_qty
            line.product_uom_qty = max(quoted_qty - line.lost_qty, 0.0)
            if float_is_zero(line.lost_qty, precision_digits=precision):
                line.lost_reason_id = False
            # keep both controls coherent: nothing left to deliver means the line is not sold
            line.is_sold = not float_is_zero(line.product_uom_qty, precision_digits=precision)

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

    @api.depends("invoice_lines.amount_currency")
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        # Odoo sums the company-currency balance, which does not net to zero when the down payment
        # was invoiced and deducted at different rates: check it in the order currency instead.
        for line in self.filtered("is_downpayment"):
            amount = 0.0
            for invoice_line in line._get_invoice_lines():
                move = invoice_line.move_id
                if move.state == "cancel" and move.payment_state != "invoicing_legacy":
                    continue
                amount += invoice_line.currency_id._convert(
                    invoice_line.amount_currency,
                    line.currency_id,
                    invoice_line.company_id,
                    move.invoice_date or move.date or fields.Date.context_today(line),
                )
            line.qty_invoiced = 0 if line.currency_id.is_zero(amount) else 1

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
