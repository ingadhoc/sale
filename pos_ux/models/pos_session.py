##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from odoo.exceptions import UserError


class PosSession(models.Model):

    _inherit = 'pos.session'

    @api.multi
    def action_pos_session_close(self):
        """ Delete statements related to outstanding payment journals in order
        to not reconcile lines.
        """
        for session in self:
            statements = session.statement_ids.filtered(
                "journal_id.pos_outstanding_payment")
            for st in statements:
                if st.line_ids.filtered(lambda x: not x.partner_id):
                    raise UserError(
                        _('You can only use %s if the customer is defined.') %
                        (', '.join(
                            [journal.name
                             for journal in
                             st.line_ids.mapped("journal_id")])))
                st.unlink()
        return super(PosSession, self).action_pos_session_close()
