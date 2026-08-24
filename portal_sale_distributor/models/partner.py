# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_limit = fields.Float(
        groups="account.group_account_invoice,account.group_account_readonly,portal_sale_distributor.group_portal_backend_distributor"
    )

    @api.model
    @api.readonly
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        # Do not move to _search: the ORM uses it to resolve the child_of of other record rules
        # and overriding it breaks the login.
        if self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            domain = Domain.AND(
                [
                    domain or [],
                    [("id", "child_of", self.env.user.commercial_partner_id.id)],
                ]
            )
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)
