import json
import logging
from datetime import datetime, timezone

from odoo import Command, api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class SaleOfflineOrder(models.Model):
    """Raw inbox of orders sent by the offline app.

    Write-optimized on purpose: only the idempotency key and the JSON payload are
    stored, inserted in bulk with plain SQL (see ``_receive``). Everything shown in
    the backend is computed from the payload at read time.
    """

    _name = "sale.offline.order"
    _description = "Offline Sale Order"
    _order = "id desc"
    _rec_name = "uuid"

    uuid = fields.Char(required=True, readonly=True)
    payload = fields.Json(readonly=True)

    payload_text = fields.Text(string="Payload (JSON)", compute="_compute_payload_fields")
    partner_name = fields.Char(string="Customer", compute="_compute_payload_fields")
    amount_total = fields.Float(compute="_compute_payload_fields")
    line_count = fields.Integer(string="Lines", compute="_compute_payload_fields")

    # Reverse links: no column here, so converting never writes on the inbox.
    sale_order_ids = fields.One2many("sale.order", "offline_order_id", string="Sale Orders")
    error_ids = fields.One2many("sale.offline.order.error", "offline_order_id", string="Errors")
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", compute="_compute_conversion")
    error_message = fields.Text(compute="_compute_conversion")
    conversion_state = fields.Selection(
        [("pending", "Pending"), ("done", "Converted"), ("error", "Error")],
        compute="_compute_conversion",
        search="_search_conversion_state",
    )

    _uuid_unique = models.Constraint("UNIQUE(uuid)", "This offline order was already received.")

    @api.depends("payload")
    def _compute_payload_fields(self):
        for record in self:
            payload = record.payload or {}
            record.payload_text = json.dumps(payload, indent=2, ensure_ascii=False) if payload else False
            record.partner_name = payload.get("partner_name")
            record.amount_total = payload.get("amount_total") or 0.0
            record.line_count = len(payload.get("lines") or [])

    @api.depends("sale_order_ids", "error_ids")
    def _compute_conversion(self):
        for record in self:
            record.sale_order_id = record.sale_order_ids[:1]
            record.error_message = record.error_ids[:1].message
            if record.sale_order_ids:
                record.conversion_state = "done"
            elif record.error_ids:
                record.conversion_state = "error"
            else:
                record.conversion_state = "pending"

    def _search_conversion_state(self, operator, value):
        if operator != "in":
            return NotImplemented
        domains = {
            "pending": [("sale_order_ids", "=", False), ("error_ids", "=", False)],
            "done": [("sale_order_ids", "!=", False)],
            "error": [("sale_order_ids", "=", False), ("error_ids", "!=", False)],
        }
        return Domain.OR(domains[state] for state in value if state in domains)

    def action_convert(self):
        self.filtered(lambda r: r.conversion_state == "pending")._convert_to_sale_orders()

    def action_retry(self):
        self.error_ids.unlink()

    @api.model
    def _cron_convert_pending(self, batch_size=100):
        while offline_orders := self._lock_pending(batch_size):
            offline_orders._convert_to_sale_orders()
            if self.env["ir.cron"]._commit_progress(len(offline_orders)) <= 0:
                break

    @api.model
    def _lock_pending(self, limit):
        # SKIP LOCKED: concurrent runs never pick the same orders.
        self.env.cr.execute(
            SQL(
                """
                SELECT o.id
                  FROM sale_offline_order o
                 WHERE NOT EXISTS (SELECT 1 FROM sale_order s WHERE s.offline_order_id = o.id)
                   AND NOT EXISTS (SELECT 1 FROM sale_offline_order_error e WHERE e.offline_order_id = o.id)
                 ORDER BY o.id
                 LIMIT %s
                   FOR UPDATE OF o SKIP LOCKED
                """,
                limit,
            )
        )
        return self.browse([row[0] for row in self.env.cr.fetchall()])

    def _convert_to_sale_orders(self):
        for offline_order in self:
            try:
                with self.env.cr.savepoint():
                    offline_order._create_sale_order()
            except Exception as error:  # noqa: BLE001 - one bad order must not stop the batch
                _logger.info("Offline order %s not converted: %s", offline_order.uuid, error)
                self.env["sale.offline.order.error"].sudo().create(
                    {"offline_order_id": offline_order.id, "message": str(error)}
                )

    def _create_sale_order(self):
        """Build and confirm the sale order exactly as the app computed it: prices
        and taxes come from the payload, they are not recomputed."""
        self.ensure_one()
        payload = self.payload or {}
        user = self.create_uid
        created = datetime.fromisoformat(payload["created_on_device"].replace("Z", "+00:00"))
        values = {
            "offline_order_id": self.id,
            "partner_id": payload["partner_id"],
            "user_id": user.id,
            "company_id": user.company_id.id,
            "date_order": created.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0),
            "order_line": [
                Command.create(
                    {
                        "product_id": line["product_id"],
                        "product_uom_qty": line["quantity"],
                        "price_unit": line["price_unit"],
                        "tax_ids": [Command.set(line.get("tax_ids") or [])],
                    }
                )
                for line in payload["lines"]
            ],
        }
        if payload.get("fiscal_position_id"):
            values["fiscal_position_id"] = payload["fiscal_position_id"]
        order = self.env["sale.order"].with_user(user).with_company(user.company_id).create(values)
        order.action_confirm()
        # Done activities are archived: never close the same visit twice.
        activity = self.env["mail.activity"].with_user(user).browse(payload.get("activity_id") or []).exists()
        if activity := activity.filtered("active"):
            activity.action_feedback(feedback=self.env._("Order %s taken from the offline app", order.name))
        return order

    @api.model
    def _receive(self, orders):
        """Insert orders for the current user in a single statement.

        :param list orders: dicts with ``uuid`` and ``payload``.
        :returns: the uuids actually inserted; the others were already there.
        """
        if not orders:
            return []
        uid = self.env.uid
        now = fields.Datetime.now()
        rows = SQL(", ").join(
            SQL("(%s, %s::jsonb, %s, %s, %s, %s)", order["uuid"], json.dumps(order["payload"]), uid, now, uid, now)
            for order in orders
        )
        self.env.cr.execute(
            SQL(
                """
                INSERT INTO sale_offline_order (uuid, payload, create_uid, create_date, write_uid, write_date)
                VALUES %s
                ON CONFLICT (uuid) DO NOTHING
                RETURNING uuid
                """,
                rows,
            )
        )
        return [row[0] for row in self.env.cr.fetchall()]
