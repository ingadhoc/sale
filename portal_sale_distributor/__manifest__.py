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
    'name': 'Portal Distributor Sale',
    'version': '13.0.1.3.0',
    'category': 'Tools',
    'complexity': 'easy',
    'author': 'ADHOC SA, Odoo Community Association (OCA)',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'depends': [
        'sale_exception',
        'price_security',
        'delivery',
        'sale_ux',
        'sale_management',
        'portal_backend',
    ],
    'demo': [
    ],
    'data': [
        'security/portal_sale_distributor_security.xml',
        'security/ir.model.access.csv',
        'views/portal_sale_views.xml',
        'views/portal_my_account_views.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
