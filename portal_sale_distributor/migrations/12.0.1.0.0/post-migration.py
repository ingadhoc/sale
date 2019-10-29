from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'portal_sale_distributor',
        'migrations/12.0.1.0.0/mig_data.xml')
