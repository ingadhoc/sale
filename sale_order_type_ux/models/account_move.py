##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('sale_type_id')
    def _compute_sale_type_id(self):
        super()._compute_sale_type_id()
        if self.sale_type_id.journal_id:
            self._onchange_journal()

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id and self.journal_id.currency_id:
            new_currency = self.journal_id.currency_id
            if new_currency != self.currency_id:
                self.currency_id = new_currency
                self._onchange_currency()
        if self.state == 'draft' and self._get_last_sequence(lock=False) and self.name and self.name != '/':
            self.name = '/'

