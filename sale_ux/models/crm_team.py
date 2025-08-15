from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    def _domain_member_ids(self):
        if self.env.user.has_group("sale_ux.group_allow_any_user_as_salesman"):
            return []
        else:
            return "['&', ('share', '=', False), ('company_ids', 'in', member_company_ids)]"

    member_ids = fields.Many2many(domain=lambda self: self._domain_member_ids())
