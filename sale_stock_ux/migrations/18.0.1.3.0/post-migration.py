##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """
    Migration script to handle removal of 'no' state from delivery_status field.

    This migration recalculates delivery_status for sale orders and sale order lines
    that previously had delivery_status = 'no' and cleans up force_delivery_status.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute("""
        SELECT id
        FROM sale_order
        WHERE delivery_status = 'no'
    """)
    order_ids = [row[0] for row in cr.fetchall()]
    if order_ids:
        orders = env["sale.order"].browse(order_ids)
        orders._compute_delivery_status()

    cr.execute("""
        SELECT id
        FROM sale_order_line
        WHERE delivery_status = 'no'
    """)
    line_ids = [row[0] for row in cr.fetchall()]
    if line_ids:
        lines = env["sale.order.line"].browse(line_ids)
        lines._compute_delivery_status()

    cr.execute("""
        SELECT COUNT(*)
        FROM sale_order
        WHERE force_delivery_status = 'no'
    """)
    force_count = cr.fetchone()[0]
    if force_count > 0:
        cr.execute("""
            UPDATE sale_order
            SET force_delivery_status = NULL
            WHERE force_delivery_status = 'no'
        """)
