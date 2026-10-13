##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

BRIDGE = "sale_order_type_invoice_policy_project"


def migrate(cr, version):
    """Hand services_delivered over to the bridge module before the loader
    sees it as an orphan field and drops its column.

    If the bridge was installed before this module was upgraded, it already
    owns its own xmlid for the field, so ours is dropped instead of renamed.
    """
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = %s
         WHERE module = 'sale_order_type_invoice_policy'
           AND model = 'ir.model.fields'
           AND name = 'field_sale_order_type__services_delivered'
           AND NOT EXISTS (
               SELECT 1 FROM ir_model_data
                WHERE module = %s
                  AND name = 'field_sale_order_type__services_delivered'
           )
        """,
        (BRIDGE, BRIDGE),
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'sale_order_type_invoice_policy'
           AND model = 'ir.model.fields'
           AND name = 'field_sale_order_type__services_delivered'
        """
    )
