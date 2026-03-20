import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Create and populate invoice_company_id for existing sale order types.

    This migration creates the invoice_company_id column and populates it for
    existing sale order types to avoid a full recomputation on large databases.

    The value is copied from company_id, which matches the compute logic.
    """
    _logger.info("Creating and populating invoice_company_id on sale_order_type")

    # Check if the column already exists.
    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'sale_order_type'
          AND column_name = 'invoice_company_id'
          AND table_schema = current_schema()
        """
    )

    if not cr.fetchone():
        _logger.info("Creating invoice_company_id column")
        cr.execute(
            """
            ALTER TABLE sale_order_type
            ADD COLUMN invoice_company_id INTEGER
            REFERENCES res_company(id) ON DELETE SET NULL
            """
        )
    else:
        _logger.info("Column invoice_company_id already exists, skipping creation")

    # Populate only missing values from company_id (same logic as compute method).
    cr.execute(
        """
        UPDATE sale_order_type sot
        SET invoice_company_id = aj.company_id
        FROM account_journal aj
        WHERE aj.id = sot.journal_id
        AND sot.invoice_company_id IS NULL
        AND sot.journal_id IS NOT NULL
        """
    )

    rows_updated = cr.rowcount
    _logger.info("Updated %s sale order types with invoice company", rows_updated)
