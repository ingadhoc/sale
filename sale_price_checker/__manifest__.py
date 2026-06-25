##############################################################################
#
#    Copyright (C) 2026  ADHOC SA  (http://www.adhoc.com.ar)
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
    "name": "Sale Price Checker",
    "version": "19.0.1.1.0",
    "category": "Sales",
    "sequence": 14,
    "summary": "Public web price checker by barcode for in-store kiosks",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "barcodes",
        "sale",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
        "views/price_checker_templates.xml",
    ],
    "assets": {
        "sale_price_checker.assets_price_checker": [
            ("include", "web.assets_frontend"),
            "barcodes/static/src/barcode_service.js",
            "sale_price_checker/static/src/price_checker.scss",
            "sale_price_checker/static/src/price_checker.xml",
            "sale_price_checker/static/src/price_checker.js",
        ],
    },
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
