from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    # on v9 value was stored on manually_set_delivered
    openupgrade.logged_query(env.cr, """
        UPDATE sale_order
        SET force_delivery_status = 'delivered'
        WHERE manually_set_delivered = True
    """,)
