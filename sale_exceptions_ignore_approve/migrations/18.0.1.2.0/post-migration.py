import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Ignoring used to set the flag without confirming, and the flag kept the
    # quotation out of every later detection, blocking rules included.
    env = api.Environment(cr, SUPERUSER_ID, {})
    orders = env["sale.order"].search([("ignore_exception", "=", True), ("state", "in", ["draft", "sent"])])
    if not orders:
        return
    orders.write({"ignore_exception": False})
    env.flush_all()
    _logger.info("Cleared the ignore exceptions flag of %s quotations", len(orders))
