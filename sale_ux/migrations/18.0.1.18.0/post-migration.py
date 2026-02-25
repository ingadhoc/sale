import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if "image_sale_order" in env["product.template"]._fields:
        product_ids = env["product.template"].search([("image_128", "!=", False), ("image_sale_order", "=", False)])
        for i in range(0, len(product_ids), 100):
            product_chunk = product_ids[i : i + 100]
            product_chunk._compute_image_sale_order()
            _logger.info("Recomputed image_sale_order for %d products", i + 100)
