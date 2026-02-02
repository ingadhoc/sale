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
    "name": "Sale UX",
<<<<<<< c4d935f3151acf7174f80ea11d3f08ac27f36df8
    "version": "19.0.1.3.0",
||||||| c71a3df116b61c2ef21ba3f851bbaa82ada39f10
    "version": "18.0.1.16.0",
=======
    "version": "18.0.1.17.0",
>>>>>>> f81e55a394696d593304ca43f0244fa0bfdd57e5
    "category": "Sales",
    "sequence": 14,
    "summary": "",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "sale",
        "account_ux",
        "sale_management",
    ],
    "data": [
        "wizards/sale_global_discount_wizard_views.xml",
        "wizards/sale_advance_payment_inv_views.xml",
        "security/sale_ux_security.xml",
        "security/ir.model.access.csv",
        "views/account_views.xml",
        "views/sale_order_views.xml",
        "views/sale_order_line_views.xml",
        "views/sale_reports.xml",
        "views/sale_portal_template.xml",
        "views/res_partner_view.xml",
        "views/res_config_settings_views.xml",
        "views/account_fiscal_position_views.xml",
        "views/product_template_views.xml",
        "data/ir_config_parameter_data.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_ux/static/src/js/sale_product_field.js",
        ],
    },
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
