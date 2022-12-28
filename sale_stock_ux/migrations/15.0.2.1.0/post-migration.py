from openupgradelib import openupgrade
import logging

logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    logger.info('Forzamos la actualizacion del reporte de factura en sale_stock porque necesitamos que este solventado el problema con el metodo _get_invoiced_lot_values')
    openupgrade.load_data(
        env.cr, 'stock_account', 'views/report_invoice.xml')
