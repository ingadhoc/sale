# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenUpgrade module for Odoo
#    @copyright 2015-Today: Odoo Community Association
#    @author: Stephane LE CORNEC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    cr = env.cr
    cr.execute(
        "select id, %s, %s, %s FROM sale_order_type" % (
            openupgrade.get_legacy_name('validate_automatically_picking'),
            openupgrade.get_legacy_name('validate_automatically_invoice'),
            openupgrade.get_legacy_name('validate_automatically_payment'),
        ))
    for rec in cr.fetchall():
        (
            id,
            validate_automatically_picking,
            validate_automatically_invoice,
            validate_automatically_payment) = rec
        so_type = env['sale.order.type'].browse(id)
        if validate_automatically_picking:
            so_type.picking_atomation = 'validate'
        # before, if we have a journal configured, we automatically create
        # invoice
        if so_type.journal_id:
            so_type.invoicing_atomation = 'create_invoice'
            if validate_automatically_invoice:
                so_type.invoicing_atomation = 'validate_invoice'
                if so_type.payment_journal_id:
                    so_type.invoicing_atomation = 'invoice_draft_payment'
                    if validate_automatically_payment:
                        so_type.invoicing_atomation = 'invoice_payment'
