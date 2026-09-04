from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import str2bool


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_gathering = fields.Boolean("Is Gathering?")
    gathering_balance = fields.Float(
        compute="_compute_gathering_balance",
        digits="Product Price",
        store=True,
        tracking=True,
        help="Balance entre la factura de acopio/anticipo y los retiros de mercaderia que realizo el cliente. Monto positivo es a favor del cliente",
    )
    gathering_amount_with_taxes = fields.Float(compute="_compute_gathering_amount", help="Monto acopiado inicialmente.")
    has_gathering_invoice = fields.Boolean(compute="_compute_has_gathering_invoice")
    withdrawn_amount = fields.Float(
        compute="_compute_withdrawn_amount",
        help="El monto retirado (o solicitado) se calcula en base a la columna cantidad de las lineas de ventas, no necesariamente tienen que estar entregadas/facturadas esas lineas de venta.",
    )

    def _get_gathering_lines(self):
        self.ensure_one()
        return self.order_line

    def _invalidate_invoices_cache(self):
        """Drop the cached invoice relations so they can be re-read through `sudo()`.

        `invoice_ids` is computed from `order_line.invoice_lines`, which the
        multi-company record rule on `account.move.line` filters out: when the
        gathering invoice belongs to a company the user has disabled, the relation
        comes back empty and the order looks uninvoiced. The empty value stays in
        the cache and survives the `sudo()`, so it has to be dropped first.
        """
        self.order_line.invalidate_recordset(["invoice_lines"])
        self.invalidate_recordset(["invoice_ids"])

    @api.depends(
        "is_gathering",
        "state",
        "order_line.product_id",
        "order_line.price_unit",
        "order_line.product_uom_qty",
        "order_line.is_downpayment",
        "order_line.quantity_returned",
        "order_line.invoice_lines.parent_state",
    )
    def _compute_gathering_balance(self):
        orders_gathering = self.filtered(
            lambda order: (
                order.is_gathering and order.state == "sale" and any(order.order_line.filtered("is_downpayment"))
            )
        )

        # invoice_lines may be cached empty from a read under a restricted
        # multi-company context, which would zero the down payment
        downpayment_lines = orders_gathering.order_line.filtered(
            lambda line: line.is_downpayment and not line.display_type
        )
        if downpayment_lines:
            downpayment_lines.invalidate_recordset(["invoice_lines"])

        for order in orders_gathering:
            lines = order._get_gathering_lines()
            total_downpayment_amount = 0
            for line in lines.filtered(
                lambda l: l.is_downpayment
                and not l.display_type
                and any(
                    il.parent_state != "cancel"
                    for il in l.sudo().invoice_lines
                    if len(il.move_id.invoice_line_ids.sale_line_ids.filtered("is_downpayment")) == 1
                )
            ):
                total_downpayment_amount += line.tax_id.with_context(round=False).compute_all(
                    line.price_unit,
                    currency=line.currency_id,
                    quantity=1,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )["total_included"]

            total_amount = 0
            for line in lines.filtered(lambda x: not x.is_downpayment):
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                total_amount += line.tax_id.compute_all(
                    price_reduce,
                    currency=line.currency_id,
                    quantity=line.product_uom_qty - line.quantity_returned,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )["total_included"]

            order.gathering_balance = total_downpayment_amount - total_amount

        (self - orders_gathering).gathering_balance = 0

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        invoiceable_lines = super()._get_invoiceable_lines(final=final)
        for rec in self.filtered(lambda x: x.is_gathering and x.gathering_balance >= -1.0):
            for line in rec.order_line.filtered("is_downpayment"):
                if final:
                    invoiceable_lines |= line
            invoiceable_lines = invoiceable_lines.filtered(
                lambda line: line.display_type not in ["line_section", "line_note"]
            )
        return invoiceable_lines

    @api.constrains("is_gathering", "amount_total")
    def _check_gathering_balance(self):
        for rec in self.filtered("is_gathering"):
            if rec.gathering_balance < -1:
                raise ValidationError(
                    _(
                        "The gathering balance will be negative (%s), you cannot make this modification to the order. Order: %s"
                    )
                    % (rec.gathering_balance, rec.name)
                )

    def _action_confirm(self):
        for order in self.filtered("is_gathering"):
            if not order.amount_total:
                raise ValidationError(
                    _("You cannot confirm a gathering order (%s) with a total amount of 0.") % order.name
                )
            lines_commands = []
            for line in order._get_gathering_lines().filtered(lambda l: l.product_uom_qty > 0):
                lines_commands.append(
                    Command.update(line.id, {"initial_qty_gathered": line.product_uom_qty, "product_uom_qty": 0})
                )
            if lines_commands:
                # for compatibility with sale_exception
                order.with_context(check_exception=False).write({"order_line": lines_commands})
        return super()._action_confirm()

    @api.depends("order_line.initial_qty_gathered", "is_gathering")
    def _compute_gathering_amount(self):
        orders_gathering = self.filtered(
            lambda x: x.is_gathering and x.order_line.filtered(lambda x: x.initial_qty_gathered > 0)
        )
        for order in orders_gathering:
            lines = order._get_gathering_lines()
            price_subtotal_with_taxes = 0
            for line in lines.filtered(lambda x: x.initial_qty_gathered > 0):
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                subtotal = line.tax_id.compute_all(
                    price_reduce,
                    currency=line.currency_id,
                    quantity=line.initial_qty_gathered,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )
                price_subtotal_with_taxes += subtotal["total_included"]
            order.gathering_amount_with_taxes = price_subtotal_with_taxes
        (self - orders_gathering).gathering_amount_with_taxes = 0.0

    @api.depends("is_gathering", "invoice_ids", "invoice_ids.state")
    def _compute_has_gathering_invoice(self):
        orders_gathering = self.filtered("is_gathering")
        orders_gathering._invalidate_invoices_cache()
        for rec in orders_gathering:
            rec.has_gathering_invoice = any(
                invoice._is_downpayment() for invoice in rec.sudo().invoice_ids if invoice.state != "cancel"
            )
        (self - orders_gathering).has_gathering_invoice = False

    def action_lock(self):
        super(SaleOrder, self - self.filtered("is_gathering")).action_lock()

    @api.depends("gathering_balance", "gathering_amount_with_taxes")
    def _compute_withdrawn_amount(self):
        orders = self.filtered("is_gathering")
        for rec in orders:
            rec.withdrawn_amount = rec.gathering_amount_with_taxes - rec.gathering_balance
        (self - orders).withdrawn_amount = 0.0

    def lock_sale_order(self):
        res = super().lock_sale_order()
        return res if not self.is_gathering else self.state == "sale"

    def _get_protected_fields(self):
        return super()._get_protected_fields() + ["is_gathering"]

    def _create_invoices(self, grouped=False, final=False, date=None):
        if self.env.context.get("invoice_gathering"):
            split_invoice_and_credit_note = str2bool(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("sale_gathering.split_invoice_and_credit_note", "False")
            )
            if split_invoice_and_credit_note:
                downpayment_invoice = super()._create_invoices(final=True, grouped=grouped, date=date)

                downpayment_invoice.invoice_line_ids.filtered(lambda x: not x.is_downpayment).unlink()
                # usamos final=True aca tambien porque si no en los casos de devoluciones no funcionaba crear la
                # factura por los productos devueltos
                products_invoice = super()._create_invoices(final=True, grouped=grouped, date=date)
                # cuando borramos las lineas de anticipo borramos tmb la linea de seccion que crea odoo
                # lo podemos hacer porque en realidad en "_get_invoiceable_lines" en acopios, solo estamos mandando a facturas
                # líneas normales (nunca notas ni secciones)
                products_invoice.invoice_line_ids.filtered(
                    lambda x: x.is_downpayment or x.display_type in ["line_section"]
                ).unlink()

                invoices = downpayment_invoice + products_invoice
                if moves_to_switch := invoices.sudo().filtered(lambda m: m.amount_total < 0):
                    with self.env.protecting([invoices._fields["team_id"]], moves_to_switch):
                        moves_to_switch.action_switch_move_type()
                if downpayment_invoice.move_type == "out_refund":
                    downpayment_invoice.reversed_entry_id = products_invoice
                    invoices.write({"ref": "Canje"})
                else:
                    products_invoice.reversed_entry_id = downpayment_invoice
                    invoices.write({"ref": "Devolución Canje"})
                invoices = invoices.sorted(lambda m: 0 if m.move_type == "out_invoice" else 1)
            else:
                invoices = super()._create_invoices(final=True, grouped=grouped, date=date)
            return invoices
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    def _create_account_invoices(self, invoice_vals_list, final):
        """Actualizacion de importes de acopio cuando facturas involucra acopios"""
        invoices = super()._create_account_invoices(invoice_vals_list, final)
        if self._context.get("invoice_gathering"):
            for invoice in invoices:
                downpayment_lines = invoice.invoice_line_ids.filtered("is_downpayment")
                if not downpayment_lines:
                    continue

                # Si viene por contexto uso esa factura (es porque se hizo el split FC + NC) y sino uso invoices
                gathering_invoice = self._context.get("gathering_invoice", invoice)
                regular_lines = gathering_invoice.invoice_line_ids.filtered(
                    lambda l: not l.is_downpayment and l.display_type == "product"
                )
                if not regular_lines:
                    continue

                tax_groups = {}
                for line in regular_lines:
                    if line.sale_line_ids:
                        tax_key = frozenset(line.sale_line_ids.tax_id.ids)
                        tax_groups.setdefault(tax_key, 0.0)
                        tax_groups[tax_key] += line.price_subtotal

                for downpayment_line in downpayment_lines:
                    if downpayment_line.sale_line_ids:
                        downpayment_tax_key = frozenset(downpayment_line.sale_line_ids.tax_id.ids)
                        amount_for_this_tax_group = tax_groups.get(downpayment_tax_key, 0.0)
                        if amount_for_this_tax_group < 0.0:
                            sign = -1.0
                        else:
                            sign = 1.0
                        downpayment_line.write(
                            {
                                "price_unit": amount_for_this_tax_group * sign,
                                "quantity": -1.0 * sign,
                            }
                        )
        return invoices
