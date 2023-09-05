##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    note = fields.Html(string="Pricelist's Description", translate=True,
                       help="Si define este campo se agregará esta leyenda en los pdf de pedidos de venta y facturas. En el caso de facturas solo se agregará si la factura esta vinculada a ordenes de venta con misma tarifa")
