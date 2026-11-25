import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ProductTemplate = env["product.template"]
    product_ids = ProductTemplate.search([("image_128", "!=", False), ("image_sale_order", "=", False)]).ids
    for i in range(0, len(product_ids), 100):
        # Browse each chunk on its own so prefetch stays inside it, and drop
        # the cache after writing: images are heavy and would pile up in memory.
        product_chunk = ProductTemplate.browse(product_ids[i : i + 100])
        product_chunk._compute_image_sale_order()
        env.invalidate_all()
        _logger.info("Recomputed image_sale_order for %d products", min(i + 100, len(product_ids)))
