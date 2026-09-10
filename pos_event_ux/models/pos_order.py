from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        registrations = self.lines.event_registration_ids
        if registrations:
            self.env.flush_all()
            for records in (registrations.event_id, registrations.event_ticket_id):
                records.invalidate_recordset(["seats_reserved", "seats_available", "seats_used", "seats_taken"])
                records._check_seats_availability()
        return res
