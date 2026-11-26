##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class BaseExceptionMethod(models.AbstractModel):
    _inherit = "base.exception.method"

    def _get_base_domain(self):
        """Let the ignore button re-evaluate a record that is already ignored.

        The base domain leaves the ignored records out of every detection, so
        without this the rules could never be checked again once the flag is set.
        """
        if self.env.context.get("recheck_ignored_exceptions"):
            return []
        return super()._get_base_domain()
