from collections import defaultdict

from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _process_saved_order(self, draft):
        if not draft and self.state != "cancel":
            self._check_event_seats_availability()
        return super()._process_saved_order(draft)

    def _check_event_seats_availability(self):
        # The standard guard only looks at confirmed registrations, and the PoS confirms them from
        # action_pos_order_paid, whose exceptions _process_saved_order catches and only logs. So ask
        # for room for the registrations about to be confirmed, before confirming them.
        registrations = self.lines.event_registration_ids.filtered(
            lambda registration: registration.state not in ("open", "done", "cancel")
        )
        if not registrations:
            return
        seats_fields = ["seats_reserved", "seats_available", "seats_used", "seats_taken"]
        registrations.event_id.invalidate_recordset(seats_fields)
        registrations.event_ticket_id.invalidate_recordset(seats_fields)
        for fname in ("event_id", "event_ticket_id"):
            needed = defaultdict(int)
            for registration in registrations:
                if registration[fname]:
                    needed[registration[fname]] += 1
            for record, count in needed.items():
                record._check_seats_availability(minimal_availability=count)
