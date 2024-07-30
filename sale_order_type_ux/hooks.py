##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

def post_init_hook(env):
    default_sale_order_type = env.ref('sale_order_type_ux.default_sale_order_type')
    sale_orders = env['sale.order'].search([('state', 'in', ['sale', 'done'])])
    sale_orders.write({'type_id': default_sale_order_type.id})
