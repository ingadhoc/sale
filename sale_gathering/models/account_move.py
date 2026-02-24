from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        down_payment_lines = self.line_ids.filtered(
            lambda line: line.is_downpayment and line.sale_line_ids.order_id.is_gathering
        )

        sale_lines_data = []
        for move_line in down_payment_lines:
            for sale_line in move_line.sale_line_ids:
                sale_lines_data.append((sale_line, sale_line.tax_ids.ids, sale_line.price_unit))

        res = super().action_post()

        for sale_line, tax_ids, price_unit in sale_lines_data:
            sale_line.write(
                {
<<<<<<< 4b4fcfece4d0d7e7583bc825a5c50b98d24e3d22
                    "tax_ids": [(6, 0, tax_ids)],
||||||| 0ba3b299f90060286fabdef7be878b6d2bf7eb15
                    "tax_id": tax_id,
=======
>>>>>>> fcbc0bfb78f3647534fe834aa8ede95220384580
                    "price_unit": price_unit,
                }
            )
        return res

    def _post(self, soft=True):
        # Odoo only auto-reconciles when credit note is posted after invoice, not vice versa

        reversed_entries = {}
        # Temporarily unlink reversed_entry_id to avoid validation error when posting invoices with afip connecting journal
        # as the reversed entry is still in draft state and l10n_latam_document_number is not set yet, this leads to a validation error.
        for move in self.filtered(lambda m: m.reversed_entry_id and m.reversed_entry_id.state == "draft"):
            reversed_entries[move] = move.reversed_entry_id
            move.reversed_entry_id = False
        result = super()._post(soft=soft)

        for move, rev in reversed_entries.items():
            move.reversed_entry_id = rev

        for move in self.filtered(lambda m: m.state == "posted" and m.move_type == "out_invoice"):
            is_gathering_sale = any(
                line.sale_line_ids.order_id.is_gathering for line in move.invoice_line_ids if line.sale_line_ids
            )
            if not is_gathering_sale:
                continue
            credit_notes = self.env["account.move"].search(
                [("reversed_entry_id", "=", move.id), ("state", "=", "posted"), ("move_type", "=", "out_refund")],
                limit=1,
            )
            if credit_notes:
                move._reconcile_reversed_moves(credit_notes, False)
        return result
