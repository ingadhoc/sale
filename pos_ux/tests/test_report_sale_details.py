from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReportSaleDetails(TransactionCase):
    """The closing difference of a split bank payment method has to reach the
    sale details report even when the session was closed in another language."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("es_419")
        cls.company = cls.env.company

        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)], limit=1
        )
        account_model = cls.env["account.account"]
        if not cls.bank_journal.profit_account_id:
            cls.bank_journal.profit_account_id = account_model.search(
                [("account_type", "=", "income_other"), ("company_ids", "in", cls.company.id)], limit=1
            )
        if not cls.bank_journal.loss_account_id:
            cls.bank_journal.loss_account_id = account_model.search(
                [("account_type", "=", "expense"), ("company_ids", "in", cls.company.id)], limit=1
            )
        cls.outstanding_account = account_model.search(
            [("account_type", "=", "asset_current"), ("company_ids", "in", cls.company.id)], limit=1
        )

        cls.payment_method = cls.env["pos.payment.method"].create(
            {
                "name": "Card UX",
                "journal_id": cls.bank_journal.id,
                "outstanding_account_id": cls.outstanding_account.id,
                "split_transactions": True,
                "company_id": cls.company.id,
            }
        )
        cls.config = cls.env["pos.config"].create(
            {"name": "Test POS Report", "payment_method_ids": [(6, 0, cls.payment_method.ids)]}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner UX"})
        cls.product = cls.env["product.product"].create(
            {"name": "Test Product UX", "available_in_pos": True, "lst_price": 100.0}
        )

    def _open_session(self):
        session = self.env["pos.session"].create({"config_id": self.config.id, "user_id": self.env.user.id})
        session.set_opening_control(0, "")
        return session

    def _paid_order(self, session):
        order = self.env["pos.order"].create(
            {
                "session_id": session.id,
                "company_id": session.company_id.id,
                "partner_id": self.partner.id,
                "amount_tax": 0.0,
                "amount_total": 100.0,
                "amount_paid": 100.0,
                "amount_return": 0.0,
                "lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "qty": 1,
                            "price_unit": 100.0,
                            "tax_ids": [(6, 0, [])],
                            "price_subtotal": 100.0,
                            "price_subtotal_incl": 100.0,
                            "full_product_name": self.product.name,
                        },
                    )
                ],
            }
        )
        self.env["pos.payment"].create(
            {"pos_order_id": order.id, "payment_method_id": self.payment_method.id, "amount": 100.0}
        )
        order.action_pos_order_paid()
        return order

    def _difference_of(self, session):
        res = (
            self.env["report.point_of_sale.report_saledetails"]
            .with_context(lang="es_419")
            .get_sale_details(session_ids=session.ids)
        )
        row = next(p for p in res["payments"] if p.get("id") == self.payment_method.id)
        return row["money_difference"]

    def test_refs_cover_every_installed_language(self):
        session = self._open_session()
        refs = session._closing_diff_move_refs(self.payment_method)
        self.assertIn(f"Closing difference in {self.payment_method.name} ({session.name})", refs)
        self.assertIn(
            session.with_context(lang="es_419")._get_diff_account_move_ref(
                self.payment_method.with_context(lang="es_419")
            ),
            refs,
        )

    def test_difference_reported_when_closed_in_spanish(self):
        session = self._open_session()
        self._paid_order(session)
        session.with_context(lang="es_419").close_session_from_ui([[self.payment_method.id, -20.0]])
        self.assertEqual(session.state, "closed")
        self.assertEqual(self._difference_of(session), -20.0)

    def test_difference_reported_when_closed_in_english(self):
        session = self._open_session()
        self._paid_order(session)
        session.with_context(lang="en_US").close_session_from_ui([[self.payment_method.id, -20.0]])
        self.assertEqual(session.state, "closed")
        self.assertEqual(self._difference_of(session), -20.0)
