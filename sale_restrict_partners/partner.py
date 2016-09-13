# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    user_id = fields.Many2one(
        'res.users', default=lambda self: self._uid)
