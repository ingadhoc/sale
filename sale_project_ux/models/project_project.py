##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models


class Project(models.Model):
    _inherit = "project.project"

    """
    bypassing the following constraint for field service project creations:
    _sql_constraints = [
        ('company_id_required_for_fsm_project', "CHECK((is_fsm = 't' AND company_id IS NOT NULL) OR is_fsm = 'f')", 'A fsm project must be company restricted'),
    ]
    """

    _sql_constraints = [
        (
            "company_id_required_for_fsm_project",
            "CHECK((is_fsm = 't') OR is_fsm = 'f')",
            "A fsm project must be company restricted",
        ),
    ]
