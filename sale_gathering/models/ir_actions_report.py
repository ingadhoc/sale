##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class Report(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if (self._get_report(report_ref).report_name == "sale_gathering.report_saleorder_gathering_document" and res_ids and self.env['sale.order'].browse(res_ids).filtered('is_gathering')):
            return super(Report, self.with_context(landscape=True))._render_qweb_pdf(report_ref, res_ids, data)
        return super()._render_qweb_pdf(report_ref, res_ids, data)
