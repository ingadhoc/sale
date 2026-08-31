##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _send_order_notification_mail(self, mail_template):
        """No mandar el mail del template si la confirmación se abortó."""
        aborted = self.state != 'sale' and (
            mail_template == self.sale_order_template_id.mail_template_id)
        if aborted:
            return
        return super()._send_order_notification_mail(mail_template)
