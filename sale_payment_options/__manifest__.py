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
    "name": "Sale Payment Options",
    "summary": "Manage and display payment options on quotations and sales orders.",
<<<<<<< fb8580c9280a9d967d96560c2185bd7d01777b37
    "version": "19.0.1.1.0",
||||||| 9804a6bb2266ac9e01663375aaf0d37207a71018
    "version": "18.0.1.0.0",
=======
    "version": "18.0.1.1.0",
>>>>>>> 507932d0da88b4243ca657c33cdb19bfead6c158
    "category": "Sales",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "depends": ["sale", "card_installment"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/sale_payment_option_template_views.xml",
        "wizard/sale_payment_option_wizard_views.xml",
        "report/sale_order_payment_options_report.xml",
        "report/ir_actions_report.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "assets": {
        "web.assets_backend": [
            "sale_payment_options/static/src/css/sale_payment_options.css",
        ],
    },
}
