from odoo import api, models


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        res = super().get_sale_details(
            date_start=date_start,
            date_stop=date_stop,
            config_ids=config_ids,
            session_ids=session_ids,
            **kwargs,
        )
        self._fix_bank_closing_difference(res)
        return res

    @api.model
    def _fix_bank_closing_difference(self, res):
        """Recover the closing difference of split bank payment methods.

        Standard writes the difference move reference translated to the language
        of the user closing the session, but looks it up with a literal in
        English. When they differ the move is missed and the report falls back to
        a computation that always yields a zero difference.
        """
        payments = res.get("payments") or []
        PosPaymentMethod = self.env["pos.payment.method"]
        PosSession = self.env["pos.session"]

        pending = []
        for payment in payments:
            # The synthetic "Cash <session>" row carries no payment method.
            if not payment.get("id") or not payment.get("session") or payment.get("cash"):
                continue
            method = PosPaymentMethod.browse(payment["id"])
            if method.type != "bank" or not method.split_transactions:
                continue
            session = PosSession.browse(payment["session"])
            pending.append((payment, session, method))

        if not pending:
            return

        refs = set()
        for dummy, session, method in pending:
            refs.update(session._closing_diff_move_refs(method))

        moves = self.env["account.move"].search(
            [
                ("ref", "in", list(refs)),
                ("journal_id", "in", [method.journal_id.id for dummy, dummy2, method in pending]),
            ]
        )
        moves_by_ref = {move.ref: move for move in moves}

        for payment, session, method in pending:
            move = next(
                (moves_by_ref[ref] for ref in session._closing_diff_move_refs(method) if ref in moves_by_ref),
                None,
            )
            if not move:
                continue
            loss = any(line.account_id == method.journal_id.loss_account_id for line in move.line_ids)
            profit = any(line.account_id == method.journal_id.profit_account_id for line in move.line_ids)
            if not loss and not profit:
                continue
            payment["final_count"] = payment["total"]
            payment["money_difference"] = -move.amount_total if loss else move.amount_total
            payment["money_counted"] = payment["final_count"] + payment["money_difference"]
            payment["cash_moves"] = []
            if payment["money_difference"]:
                payment["cash_moves"] = [
                    {
                        "name": "Difference observed during the counting (Profit)"
                        if profit
                        else "Difference observed during the counting (Loss)",
                        "amount": payment["money_difference"],
                    }
                ]
            payment["count"] = True
