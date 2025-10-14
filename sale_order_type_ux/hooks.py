##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
def post_init_hook(env):
    default_sale_order_type = env.ref("sale_order_type_ux.default_sale_order_type")
    # usamos SQL directo para bypasear validaciones de Python (ej: sale_ux locked constraint)
    env.cr.execute(
        """
        UPDATE sale_order
        SET type_id = %s
        WHERE state IN ('sale', 'done')
          AND type_id IS NULL
    """,
        (default_sale_order_type.id,),
    )
