##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

_logger = logging.getLogger(__name__)

# One row per plan, instead of one row per option with its plans in options_json. The columns are
# created and filled here, before the ORM puts the NOT NULL on card_installment_id: on a table that
# already has rows, Odoo cannot add a required column without a value for every one of them.
ADD_COLUMNS = """
    ALTER TABLE sale_payment_option ADD COLUMN IF NOT EXISTS option_number integer;
    ALTER TABLE sale_payment_option ADD COLUMN IF NOT EXISTS card_installment_id integer;
    ALTER TABLE sale_payment_option ADD COLUMN IF NOT EXISTS percentage numeric;
"""

# The number the report was printing came from the position of the option in its order or template.
NUMBER_OPTIONS = """
    WITH numbered AS (
        SELECT id,
               row_number() OVER (
                   PARTITION BY COALESCE(sale_order_id, 0), COALESCE(payment_option_template_id, 0)
                   ORDER BY sequence, id
               ) AS option_number
          FROM sale_payment_option
    )
    UPDATE sale_payment_option opt
       SET option_number = numbered.option_number
      FROM numbered
     WHERE opt.id = numbered.id
"""

# Only plans that still exist: the amounts are computed from the plan now, so a row pointing at a
# deleted one could not be printed anyway.
PLAN_ITEMS = """
    SELECT opt.id,
           opt.sale_order_id,
           opt.payment_option_template_id,
           opt.sequence,
           opt.option_number,
           opt.create_uid,
           opt.create_date,
           item.value AS item,
           item.ordinality AS position
      FROM sale_payment_option opt
      JOIN LATERAL jsonb_array_elements(opt.options_json) WITH ORDINALITY AS item(value, ordinality)
        ON TRUE
      JOIN account_card_installment plan
        ON plan.id = (item.value->>'card_installment_id')::integer
     WHERE jsonb_typeof(opt.options_json) = 'array'
"""

FILL_FIRST_PLAN = f"""
    WITH items AS ({PLAN_ITEMS})
    UPDATE sale_payment_option opt
       SET card_installment_id = (items.item->>'card_installment_id')::integer,
           percentage = (items.item->>'percentage')::numeric / 100
      FROM items
     WHERE opt.id = items.id
       AND items.position = 1
"""

INSERT_REMAINING_PLANS = f"""
    WITH items AS ({PLAN_ITEMS})
    INSERT INTO sale_payment_option (
        sale_order_id, payment_option_template_id, sequence, option_number,
        card_installment_id, percentage, create_uid, create_date, write_uid, write_date
    )
    SELECT items.sale_order_id,
           items.payment_option_template_id,
           items.sequence,
           items.option_number,
           (items.item->>'card_installment_id')::integer,
           (items.item->>'percentage')::numeric / 100,
           items.create_uid,
           items.create_date,
           items.create_uid,
           now() AT TIME ZONE 'UTC'
      FROM items
     WHERE items.position > 1
"""

# An option whose plans were all gone, or that never had any: it printed an empty row.
DELETE_UNCONVERTED = """
    DELETE FROM sale_payment_option WHERE card_installment_id IS NULL
"""


def migrate(cr, version):
    cr.execute(ADD_COLUMNS)
    cr.execute(NUMBER_OPTIONS)
    cr.execute(FILL_FIRST_PLAN)
    cr.execute(INSERT_REMAINING_PLANS)
    cr.execute(DELETE_UNCONVERTED)
    if cr.rowcount:
        _logger.warning("sale_payment_options: dropped %s payment option rows with no installment plan", cr.rowcount)
