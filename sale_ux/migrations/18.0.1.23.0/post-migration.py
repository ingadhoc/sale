import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Down payments invoiced and deducted at different rates were left as not deducted.
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env["sale.order.line"].search([("is_downpayment", "=", True), ("qty_invoiced", "!=", 0)])
    lines = lines.filtered(lambda line: line.currency_id != line.company_id.currency_id)
    if not lines:
        return
    before = {line.id: line.qty_invoiced for line in lines}
    lines._compute_qty_invoiced()
    fixed = lines.filtered(lambda line: line.qty_invoiced != before[line.id])
    env.flush_all()
    _logger.info("Recomputed %d foreign currency down payment lines, %d fixed", len(lines), len(fixed))
