from odoo.osv import expression
from odoo.addons.sale_timesheet.models.account import AccountAnalyticLine


def _timesheet_get_portal_domain(self):
    """ WE revert this functionality of odoo. We want to show details of ordered quantities also
        Only the timesheets with a product invoiced on delivered quantity are concerned.
        since in ordered quantity, the timesheet quantity is not invoiced,
        thus there is no meaning of showing invoice with ordered quantity.
    """
    domain = super(AccountAnalyticLine, self)._timesheet_get_portal_domain()
    return expression.AND(
        [domain, [('timesheet_invoice_type', 'in', ['billable_time', 'non_billable', 'billable_fixed'])]])


AccountAnalyticLine._timesheet_get_portal_domain = _timesheet_get_portal_domain
