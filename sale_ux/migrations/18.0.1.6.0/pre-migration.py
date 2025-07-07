def migrate(cr, version):
    """Change the ir_model_data.module for group_delivery_date_on_report_online from l10n_ar_sale to sale_ux"""
    cr.execute("""
        SELECT 1 FROM ir_model_data
        WHERE module = 'l10n_ar_sale'
        AND name = 'group_delivery_date_on_report_online'
        AND model = 'res.groups'
    """)

    if not cr.fetchone():
        return

    cr.execute("""
        UPDATE ir_model_data
        SET module = 'sale_ux'
        WHERE module = 'l10n_ar_sale'
        AND name = 'group_delivery_date_on_report_online'
        AND model = 'res.groups'
    """)
