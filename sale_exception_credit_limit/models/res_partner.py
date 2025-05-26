##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    user_credit_config = fields.Boolean(compute="_compute_user_credit_config")

    @api.depends_context("uid")
    def _compute_user_credit_config(self):
        self.user_credit_config = self.env.user.has_group("sale_exception_credit_limit.credit_config")

    def write(self, vals):
        """Si esta constraint trae dolores de cabeza la podemos sacar ya que este "bache" de seguridad esta en muchos
        lugares aún mas criticos. Es un problema del ORM donde mucho se protege a nivel vista"""
        if "credit_limit" in vals or "use_partner_credit_limit" in vals:
            for record in self:
                if not self.env.user.has_group("sale_exception_credit_limit.credit_config"):
                    new_credit_limit = vals.get("credit_limit", record.credit_limit)
                    if not record.parent_id or new_credit_limit != record.parent_id.credit_limit:
                        raise ValidationError(
                            "People without Credit limit Configuration Rights cannot modify credit limit parameters"
                        )
        return super().write(vals)
