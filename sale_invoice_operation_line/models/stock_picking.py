# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # esto es solo para que funcione bien llevar valores custom desde
    # las lineas de ov cuando la factura se crea desde el picking
    # en v9 se podria borrar (y la dep al modulo stock_account)
    @api.multi
    def action_invoice_create(
            self, journal_id, group=False, type='out_invoice'):
        invoice_ids = super(StockPicking, self).action_invoice_create(
            journal_id, group=group, type=type)
        # si hay ov linkeada y tiene operaciones, borramos las operacione
        # actuales de la factura y forzamos recrearlas
        # esto es necesario asi porque sale_stock y stock_account crean
        # las lineas de a una, entonces en la primer corrida, el add_operations
        # ya crea las operaciones y luego faltan otros productos/lineas crearse
        if self.sale_id and self.sale_id.operation_ids:
            self.env['account.invoice'].browse(
                invoice_ids).operation_ids.unlink()
            self.sale_id.add_operations_to_invoices()
        return invoice_ids
