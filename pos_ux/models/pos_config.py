from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class PosConfig(models.Model):

    _inherit = 'pos.config'

    billing_behavior = fields.Selection([('on_demand','Invoice on demand'), ('invoice_by_default', 'By default invoice'),
                                         ('invoice_required', 'allways Invoice')], default='on_demand')
    block_invoice_download = fields.Boolean()

    def open_ui(self):
        for config in self:
            invalid_payment_methods = config.payment_method_ids.filtered(
            lambda method: not method.split_transactions and not method.receivable_account_id)
            if invalid_payment_methods:
                payment_method_names = ', '.join(invalid_payment_methods.mapped('name'))
                raise UserError(_("No se puede completar la operación: falta definir cuenta intermediaria en los siguientes métodos de pago: %s") % payment_method_names)
        return super().open_ui()
