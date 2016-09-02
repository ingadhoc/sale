# -*- coding: utf-8 -*-
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
    'name': 'Stock availability in sales order line',
    'version': '9.0.1.1.0',
    'category': 'Tools',
    'author': 'Moldeo Interactive & ADHOC SA',
    'website': 'http://business.moldeo.coop http://adhoc.com.ar/',
    'license': 'AGPL-3',
    'images': [],
    'depends': [
        'sale_stock'
    ],
    'demo': [],
    'data': [
        'views/sale_view.xml',
        'views/stock_view.xml',
        'security/sale_order.xml',
    ],
    'test': [],
    'installable': True,
}
