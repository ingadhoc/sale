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
    'name': 'Sale Invoice Operation Line',
    'version': '9.0.1.0.0',
    'category': 'Accounting & Finance',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        # esta dependencia es solo para que funcione llevando bien
        # los valores de las lineas al facturar desde remitos y se podria
        # borrar en v9
        'sale_stock',
        'sale_invoice_operation',
        'web_widget_x2many_2d_matrix',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/sale_order_line_operation_wizard_view.xml',
        'wizards/account_invoice_line_operation_wizard_view.xml',
        'views/account_invoice_view.xml',
        'views/sale_order_view.xml',
        'views/sale_invoice_operation_view.xml',
        'views/product_template_view.xml',
        'views/product_invoice_operation_restriction_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': False,
    'auto_install': False,
    'application': False,
}
