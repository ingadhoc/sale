##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
{
    'name': 'Sale UX',
    'version': "17.0.1.6.0",
    'category': 'Sales',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'sale',
        'account_ux',
        'sale_management',
    ],
    'data': [
        'wizards/sale_global_discount_wizard_views.xml',
        'wizards/sale_advance_payment_inv_views.xml',
        'security/sale_ux_security.xml',
        'security/ir.model.access.csv',
        'views/account_views.xml',
        'views/sale_order_views.xml',
        'views/sale_order_line_views.xml',
        'views/sale_reports.xml',
        'views/sale_portal_template.xml',
        'views/res_partner_view.xml',
        'views/res_config_settings_views.xml',
        'views/account_fiscal_position_views.xml',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
