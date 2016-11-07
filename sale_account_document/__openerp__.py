# -*- coding: utf-8 -*-
{
    'name': 'Argentinian Sale Total Fields',
    'version': '9.0.1.0.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Account Document with Sale integration
======================================
For now it only adds some computed fields similar to account_document ones.
    """,
    'depends': [
        'sale',
        'l10n_ar_account',
    ],
    'external_dependencies': {
    },
    'data': [
        'security/invoice_sale_security.xml',
        'views/sale_view.xml',
        'views/res_company_view.xml',
        # 'res_config_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
