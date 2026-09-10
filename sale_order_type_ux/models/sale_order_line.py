<<<<<<< HEAD
||||||| MERGE BASE
=======
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Quitamos el check_company ya que no permitira
    # realizar un cambio de compañia entre la venta y su factura de anticipo
    tax_id = fields.Many2many(check_company=False)

>>>>>>> FORWARD PORTED
