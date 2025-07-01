from odoo import api, fields, models


class SalePaymentOption(models.Model):
    _name = "sale.payment.option"
    _description = "Sale payment option"
    _order = "sequence"

    sequence = fields.Integer(default=10)
    payment_option_template_id = fields.Many2one("sale.payment.option.template")
    sale_order_id = fields.Many2one("sale.order", ondelete="cascade")
    options_json = fields.Json(readonly=False, compute="_compute_options_json", store=True)
    options_json_rendered = fields.Html(string="Details", compute="_compute_options_json_rendered", store=False)

    @api.depends("sale_order_id.amount_total")
    def _compute_options_json(self):
        for rec in self:
            if not rec.sale_order_id or not rec.options_json:
                continue

            updated_options = []
            for opt in rec.options_json:
                updated_opt = dict(opt)
                card_installment_id = updated_opt.get("card_installment_id")
                card_installment = self.env["account.card.installment"].browse(card_installment_id)
                if card_installment.exists():
                    order_amount = rec.sale_order_id.amount_total * updated_opt.get("percentage") / 100
                    mapped_values = card_installment.map_installment_values(order_amount)
                    subtotal = mapped_values.get("amount")
                    updated_opt.update(
                        {"subtotal": subtotal, "total_per_installment": subtotal / updated_opt.get("installment_qty")}
                    )
                updated_options.append(updated_opt)
            rec.options_json = updated_options

    def _render_options_json_table(self, template_mode=False):
        self.ensure_one()
        if not self.options_json:
            return ""

        if template_mode:
            return self._render_template_table()
        return self._render_full_table()

    def _render_template_table(self):
        table_parts = [
            '<table class="table table-sm table-bordered mb-2">',
            "<thead><tr><th>% OV</th><th>Plan de cuotas</th><th>Recargo</th></tr></thead>",
            "<tbody>",
        ]

        for opt in self.options_json:
            table_parts.append(
                f'<tr>'
                f'<td>{opt.get("percentage")}%</td>'
                f'<td>{opt.get("card_installment")}</td>'
                f'<td>{opt.get("surcharge")}%</td>'
                f'</tr>'
            )

        table_parts.extend(["</tbody>", "</table>"])
        return "".join(table_parts)

    def _render_full_table(self):
        table_parts = [
            '<table class="table table-sm table-bordered mb-2">',
            "<thead><tr>",
            '<th style="width:10%">% OV</th>'
            '<th style="width:30%">Plan de cuotas</th>'
            '<th style="width:10%">Recargo</th>'
            '<th style="width:20%">Subtotal</th>'
            '<th style="width:20%">Total por cuota</th>'
            '<th style="width:10%">Cantidad de cuotas</th>'
            "</tr></thead><tbody>",
        ]

        total_subtotal = 0
        for opt in self.options_json:
            subtotal = opt.get("subtotal", 0)
            total_subtotal += subtotal or 0

            table_parts.append(
                f'<tr>'
                f'<td style="width:10%">{opt.get("percentage", "")}%</td>'
                f'<td style="width:30%">{opt.get("card_installment", "")}</td>'
                f'<td style="width:10%">{opt.get("surcharge", "")}%</td>'
                f'<td style="width:20%">{self._format_currency(subtotal)}</td>'
                f'<td style="width:20%">{self._format_currency(opt.get("total_per_installment"))}</td>'
                f'<td style="width:10%">{opt.get("installment_qty") or "-"}</td>'
                f'</tr>'
            )

        table_parts.extend(
            [
                "</tbody>",
                "<tfoot><tr>",
                '<td colspan="3"><b>Total</b></td>',
                f"<td><b>{self._format_currency(total_subtotal)}</b></td>",
                '<td colspan="2"></td>',
                "</tr></tfoot>",
                "</table>",
            ]
        )

        return "".join(table_parts)

    def _compute_options_json_rendered(self):
        for rec in self:
            template_mode = bool(rec.payment_option_template_id)
            rec.options_json_rendered = rec._render_options_json_table(template_mode=template_mode)

    def _format_currency(self, amount):
        if not amount:
            return ""
        if self.sale_order_id and self.sale_order_id.currency_id:
            return self.sale_order_id.currency_id.format(amount)
        return f"{amount:.2f}"
