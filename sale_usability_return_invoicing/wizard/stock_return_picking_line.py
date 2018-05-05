# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund_so = fields.Boolean(
        # agregamos valor por defecto que preferimos
        # no funciona porque el default esta sobreescrito en odoo
        # lo implementamos en stock.return.picking
        # default=True,

        # actualizamos con mensajes de v11
        string='To Refund (update SO/PO)',
        help='Trigger a decrease of the delivered/received quantity in the '
        'associated Sale Order/Purchase Order',
        # lo hacemos computado desde un selection ya que el default refund
        # no se renderiza bien
        # compute='_compute_to_refund_so',
    )
