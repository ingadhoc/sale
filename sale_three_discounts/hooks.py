from odoo import SUPERUSER_ID, api
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    _logger.info('INIT HOOK: Arreglar lineas de venta que no han sido facturadas para que funcionen bien los descuentos a aplicar')
    env = api.Environment(cr, SUPERUSER_ID, {})
    invoice_lines_with_disc = env['sale.order.line'].search([('invoice_status', '!=', 'invoiced'), ('discount', '!=', 0.0)])
    for rec in invoice_lines_with_disc:
        rec.discount1 = rec.discount
