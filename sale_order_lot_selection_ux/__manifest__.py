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
    "name": "Sale Order Lot Selection UX",
<<<<<<< 50f0298c929c64a7bba8d934ecf55068577533e5
    "version": "19.0.1.0.0",
||||||| 529dc01054592d7a48d267b4c762dedb45b2e31f
    "version": "18.0.1.0.0",
=======
    "version": "18.0.1.1.0",
>>>>>>> e26c224d31fb6378d01c086999052eb1efacde0c
    "category": "Sale",
    "sequence": 14,
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "depends": [
        "sale_order_lot_selection",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/stock_production_lot.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
