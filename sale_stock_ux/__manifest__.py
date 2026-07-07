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
    "name": "Sale Stock UX",
<<<<<<< 45158847ecfb019e152733cc2218df6e704a0b9d
    "version": "19.0.1.4.0",
||||||| 53dc870e73a970e657c6909b8cf657b3ce51cf6d
    "version": "18.0.1.8.0",
=======
    "version": "18.0.1.9.0",
>>>>>>> bc26ec8c87bd1d58c86b40c36a7dfad48808da23
    "category": "Sales",
    "sequence": 14,
    "summary": "",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "sale_stock",
        "sale_ux",
        "stock_ux",
        "web",
        "product_stock_by_location",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/sale_order_line_views.xml",
        "views/stock_move_views.xml",
        "wizards/sale_order_cancel_remaining.xml",
        "wizards/stock_return_picking_views.xml",
        "wizards/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_qweb": [
            "sale_stock_ux/static/src/xml/*.xml",
        ],
        "web.assets_backend": [
            "sale_stock_ux/static/src/widgets/qty_at_date_widget.xml",
        ],
    },
    "demo": [],
    "test": [],
    "installable": True,
    "auto_install": True,
    "application": False,
}
