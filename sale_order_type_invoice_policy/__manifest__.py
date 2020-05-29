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
    'name': 'Sale Order Type Invoicing Policy',
    'version': '13.0.1.0.0',
    'category': 'Sale Management',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'sale_order_type',
        # agregamos esta depenencia para permitir reembolsar las devoluciones
        # y para no tener que hacer modulos puente
        'sale_stock_ux',
    ],
    'demo': [
        'demo/res_partner_demo.xml',
        'demo/sale_order_demo.xml',
    ],
    'data': [
        'views/sale_order_type_views.xml',
        'views/stock_picking_views.xml',
        'data/sale_order_type_data.xml',
    ],
    'installable': True,
    'auto_install': False,
}
