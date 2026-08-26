# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_limit = fields.Float(
        groups="account.group_account_invoice,account.group_account_readonly,portal_sale_distributor.group_portal_backend_distributor"
    )

    @api.model
    def web_name_search(self, name, specification, domain=None, operator="ilike", limit=100):
        """Keep the contact autocomplete working for portal users.

        On top of the display name, the web client asks for a formatted one, and computing it
        reads parent_id.name (res.partner._compute_display_name). A portal user can be allowed
        to read a contact and not its parent, and then the whole search fails with an
        AccessError instead of returning what it can read. Only the label formatting is done as
        superuser: the search itself still runs as the user, so record rules pick the results,
        and the parent name is already part of the display name of those same records.
        """
        if self.env.user.has_group("base.group_user") or list(specification) != ["display_name"]:
            return super().web_name_search(name, specification, domain=domain, operator=operator, limit=limit)
        records = self.browse([record_id for record_id, _name in self.name_search(name, domain, operator, limit)])
        formatted = records.sudo().with_context(formatted_display_name=True)
        return [
            {
                "id": record.id,
                "display_name": record.display_name,
                "__formatted_display_name": formatted_record.display_name,
            }
            for record, formatted_record in zip(records, formatted)
        ]
