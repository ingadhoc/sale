##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = "res.partner"

    user_credit_config = fields.Boolean(compute='_compute_user_credit_config')

    @api.depends_context('uid')
    def _compute_user_credit_config(self):
        self.user_credit_config = self.env.user.has_group('sale_exception_credit_limit.credit_config')

    @api.constrains('credit_limit', 'use_partner_credit_limit')
    def check_credit_limit_group(self):
        """Si esta constraint trae dolores de cabeza la podemos sacar ya que este "bache" de seguridad esta en muchos
        lugares aún mas criticos. es un problema del ORM donde mucho se protege a nivel vista"""
        if not self.env.user.has_group('sale_exception_credit_limit.credit_config') and any(
            not x.parent_id or x.credit_limit != x.parent_id.credit_limit for x in self
        ):
            raise ValidationError('People without Credit limit Configuration Rights cannot modify credit limit parameters')
