##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

BRIDGE = "sale_order_type_invoice_policy_project"


def migrate(cr, version):
    """Hand services_delivered over to the bridge module.

    The field moves to a bridge module that depends on sale_project. Two things
    have to happen before the loader treats it as an orphan and drops its column:
    the xmlid must point to the bridge, and the bridge must be installed.
    auto_install does not cover this: it only triggers when a dependency is
    itself being installed, which is not the case on an existing database.
    """
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = %s
         WHERE module = 'sale_order_type_invoice_policy'
           AND model = 'ir.model.fields'
           AND name = 'field_sale_order_type__services_delivered'
        """,
        (BRIDGE,),
    )
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'to install'
         WHERE name = %s
           AND state = 'uninstalled'
           AND EXISTS (
               SELECT 1 FROM ir_module_module
                WHERE name = 'sale_project'
                  AND state IN ('installed', 'to upgrade', 'to install')
           )
        """,
        (BRIDGE,),
    )
