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
    "name": "Sale Exception Credit Limit",
<<<<<<< 20165dd5e34fabe145ea398517faf45200c8af16
    "version": "19.0.1.1.0",
||||||| 58c8a66d6eaeb4475dc8d70b9d3ace39bd0b48fa
    "version": "18.0.1.2.0",
=======
    "version": "18.0.1.3.0",
>>>>>>> d8857e45701e4e412a414240419b15cd162fb822
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "depends": [
        "sale_exception",
        "account_multicompany_ux",
    ],
    "data": [
        "security/sale_exception_credit_limit_security.xml",
        "data/exception_rule_data.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": ["demo/res_partner_demo.xml"],
    "installable": True,
    "post_init_hook": "_post_init_credit",
}
