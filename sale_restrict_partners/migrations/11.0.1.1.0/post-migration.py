from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'sale_restrict_partners',
        'migrations/11.0.1.1.0/mig_data.xml')
