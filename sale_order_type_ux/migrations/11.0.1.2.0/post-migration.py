from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'sale_order_type_ux',
        'migrations/11.0.1.2.0/mig_data.xml')
