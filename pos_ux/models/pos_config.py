from odoo import models, fields, api


class PosConfig(models.Model):

    _inherit = 'pos.config'

    billing_behavior = fields.Selection([('on_demand','Invoice on demand'), ('invoice_by_default', 'By default invoice'),
                                         ('invoice_required', 'allways Invoice')], default='on_demand')
    block_invoice_download = fields.Boolean()
