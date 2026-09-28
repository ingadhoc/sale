##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################


def migrate(cr, version):
    """Hand services_delivered over to the bridge module before the loader
    sees it as an orphan field and drops its column."""
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'sale_order_type_invoice_policy_project'
         WHERE module = 'sale_order_type_invoice_policy'
           AND model = 'ir.model.fields'
           AND name = 'field_sale_order_type__services_delivered'
        """
    )
