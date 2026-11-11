##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models
from odoo.fields import Domain


class EventEvent(models.Model):
    _inherit = "event.event"

    portal_distributor_visible = fields.Boolean(
        compute="_compute_portal_distributor_visible",
        search="_search_portal_distributor_visible",
        help="Technical field used by the access of the portal distributor group. With website_event "
        "installed only the events published on the website are visible, as it was in 19.0; without "
        "it, all of them.",
    )

    def _compute_portal_distributor_visible(self):
        has_website = "website_published" in self._fields
        for event in self:
            event.portal_distributor_visible = event.website_published if has_website else True

    def _search_portal_distributor_visible(self, operator, value):
        # website_event is not a dependency, so website_published can not be named in the domain of the
        # access: it would raise on the databases that do not have it.
        if operator not in ("=", "!="):
            raise NotImplementedError(operator)
        visible = (operator == "=") == bool(value)
        if "website_published" not in self._fields:
            return Domain.TRUE if visible else Domain.FALSE
        return Domain("website_published", "=", True) if visible else Domain("website_published", "!=", True)
