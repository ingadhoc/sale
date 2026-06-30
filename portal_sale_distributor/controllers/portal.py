##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.http import request


class CustomerPortalDistributor(CustomerPortal):
    def _prepare_quotations_domain(self, partner):
        if request.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            return [
                ("message_partner_ids", "child_of", [partner.commercial_partner_id.id]),
                ("state", "in", ["draft", "sent"]),
            ]
        else:
            return super()._prepare_quotations_domain(partner)
