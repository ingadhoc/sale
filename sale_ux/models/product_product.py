from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _get_tax_included_unit_price(
            self, company, currency, document_date, document_type,
            is_refund_document=False, product_uom=None, product_currency=None,
            product_price_unit=None, product_taxes=None, fiscal_position=None):
        """Modificamos para que como se obtienen los precios no tenga en cuenta en nada la fiscal position.
        Sin este cambio, en una venta con posicion fiscal que reemplace IVA 21 a exento (o no gravado, si se recalcula
        el precio (cambiando cantidad o agregando producto) y el impuesto es con opcion "incluido", el precio que se
        usa es descontando el impuesto original en vezl del precio final
        """
        return super()._get_tax_included_unit_price(
            company, currency, document_date, document_type,
            is_refund_document=is_refund_document, product_uom=product_uom, product_currency=product_currency,
            product_price_unit=product_price_unit, product_taxes=product_taxes, fiscal_position=False)
