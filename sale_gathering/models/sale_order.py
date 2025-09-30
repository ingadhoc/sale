from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


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

    @api.depends(
        "is_gathering",
        "state",
        "order_line.product_id",
        "order_line.price_unit",
        "order_line.qty_invoiced",
        "order_line.qty_to_invoice",
        "order_line.is_downpayment",
        "order_line.quantity_returned",
    )
    def _compute_gathering_balance(self):
        orders_gathering = self.filtered(
            lambda order: order.is_gathering
            and order.state == "sale"
            and any(order.order_line.filtered("is_downpayment"))
        )

        for order in orders_gathering:
            total_downpayment_amount = 0
            for line in order.order_line.filtered("is_downpayment"):
                total_downpayment_amount += line.tax_id.with_context(round=False).compute_all(
                    line.price_unit,
                    currency=line.currency_id,
                    quantity=1,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )["total_included"]

            total_amount_to_invoice_invoiced = 0
            for line in order.order_line.filtered(lambda x: not x.is_downpayment):
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                total_amount_to_invoice_invoiced += line.tax_id.compute_all(
                    price_reduce,
                    currency=line.currency_id,
                    quantity=line.qty_to_invoice + line.qty_invoiced,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )["total_included"]

            order.gathering_balance = total_downpayment_amount - total_amount_to_invoice_invoiced

        (self - orders_gathering).gathering_balance = 0

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        invoiceable_lines = super()._get_invoiceable_lines(final=final)
        product_precision_digits = self.env["decimal.precision"].precision_get("Product Price")
        for rec in self.filtered(
            lambda x: x.is_gathering
            and float_compare(x.gathering_balance, 0.0, precision_digits=product_precision_digits) >= 0
        ):
            for line in rec.order_line:
                if line.is_downpayment and final:
                    invoiceable_lines |= line
                # Cuando es una devolución y no estamos agregando final=True lo nativo de Odoo no estaba agregando la línea y por lo tanto
                # no se hace nada. Adicionalmente esto solo quiero que me entre para el caso de las líneas que tienen cantidad negativa
                # por devolución y no cantidad negativa por anticipo (caso primer factura)
                elif line.qty_to_invoice < 0 and not final and not line.is_downpayment:
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
            lines_commands = []
            for line in order.order_line.filtered(lambda l: l.product_uom_qty > 0):
                lines_commands.append(
                    Command.update(line.id, {"initial_qty_gathered": line.product_uom_qty, "product_uom_qty": 0})
                )
            if lines_commands:
                order.write({"order_line": lines_commands})
        return super()._action_confirm()

    @api.depends("order_line.initial_qty_gathered", "is_gathering")
    def _compute_gathering_amount(self):
        orders_gathering = self.filtered(
            lambda x: x.is_gathering and x.order_line.filtered(lambda x: x.initial_qty_gathered > 0)
        )
        for order in orders_gathering:
            price_subtotal_with_taxes = 0
            for line in order.order_line.filtered(lambda x: x.initial_qty_gathered > 0):
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
        for rec in orders_gathering:
            rec.has_gathering_invoice = any(
                invoice._is_downpayment() for invoice in rec.invoice_ids if invoice.state != "cancel"
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

    def write(self, values):
        protected_fields = self._get_protected_fields()
        if any(state in ["sale", "done"] for state in self.mapped("state")) and any(
            f in values.keys() for f in protected_fields
        ):
            protected_fields_modified = list(set(protected_fields) & set(values.keys()))
            fields = (
                self.env["ir.model.fields"]
                .sudo()
                .search([("name", "in", protected_fields_modified), ("model", "=", self._name)])
            )
            if fields:
                raise UserError(
                    _("It is forbidden to modify the following fields in a confirmed order:\n%s")
                    % "\n".join(fields.mapped("field_description"))
                )
        return super().write(values)

    def _get_protected_fields(self):
        return ["is_gathering"]

    def _create_invoices(self, grouped=False, final=False, date=None):
        if self.env.context.get("invoice_gathering"):
            split_invoice_and_credit_note = bool(
                self.env["ir.config_parameter"].sudo().get_param("sale_gathering.split_invoice_and_credit_note", "True")
            )
            if split_invoice_and_credit_note:
                # Tenemos que enviar el contexto cuando es una devolución para que luego me lo cambie a nota de crédito
                pickings = self.env["stock.picking"].browse(self.env.context.get("picking_ids"))
                if pickings.mapped("return_id"):
                    self = self.with_context(invoice_gathering=True)
                invoices = super(SaleOrder, self)._create_invoices(final=False, grouped=grouped, date=date)
                for invoice in invoices:
                    credit_note = super(
                        SaleOrder, self.with_context(gathering_invoice=invoice, invoice_gathering=True)
                    )._create_invoices(final=True, grouped=grouped, date=date)
                    credit_note.reversed_entry_id = invoice
                    invoices += credit_note
            else:
                invoices = super()._create_invoices(final=True, grouped=grouped, date=date)
            return invoices
        return super()._create_invoices()

    def _create_account_invoices(self, invoice_vals_list, final):
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
                        downpayment_line.write(
                            {
                                "price_unit": amount_for_this_tax_group,
                                "quantity": 1.0,
                            }
                        )

                # Cuando es una devolución no tengo que cambiar a nota de crédito ya que el anticipo debe ser una factura
                pickings = self.env["stock.picking"].browse(self.env.context.get("picking_ids"))
                if self.env.context.get("gathering_invoice") and not pickings.mapped("return_id"):
                    invoice.action_switch_move_type()
            # Cuando es una devolución la cantidad total de la factura es negativa (y nativamente no lo cambia a NC debido a que tenemos final=False)
            # y nosotros lo tenemos que cambiar a NC porque sino no deja validar la factura
            if not final and (moves_to_switch := invoices.sudo().filtered(lambda m: m.amount_total < 0)):
                moves_to_switch.action_switch_move_type()
        return invoices
