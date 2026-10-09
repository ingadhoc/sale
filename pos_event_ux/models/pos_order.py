from collections import defaultdict

from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

<<<<<<< a5c67f89a56d0ccb04bcbfd7307f9e0b42f0ac32
    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        registrations = self.lines.event_registration_ids
        if registrations:
            self.env.flush_all()
            seats_fields = ["seats_reserved", "seats_available", "seats_used", "seats_taken"]
            for records in (registrations.event_id, registrations.event_slot_id, registrations.event_ticket_id):
                records.invalidate_recordset(seats_fields)
            registrations._check_seats_availability()
        return res
||||||| 00e9237f897e9f0c17252e2923cc647f9b0d40a4
    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        registrations = self.lines.event_registration_ids
        if registrations:
            self.env.flush_all()
            for records in (registrations.event_id, registrations.event_ticket_id):
                records.invalidate_recordset(["seats_reserved", "seats_available", "seats_used", "seats_taken"])
                records._check_seats_availability()
        return res
=======
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
>>>>>>> ba247bcbcad88f9a5134d912b8cdbd836a69b94a
