##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from odoo import api, SUPERUSER_ID


def _post_init_credit(env):
    env['res.company'].search([]).write({'account_use_credit_limit':True})
