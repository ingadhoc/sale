# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


column_copies = {
    'sale_order_type': [
        ('validate_automatically_picking', None, None),
        ('validate_automatically_invoice', None, None),
        # ya tenemos a todo el mundo actualizado y este campo no existia en v8
        # lo omitimos para que no de error
        # ('validate_automatically_payment', None, None),
    ],
}


@openupgrade.migrate()
def migrate(cr, version):
    openupgrade.copy_columns(cr, column_copies)
