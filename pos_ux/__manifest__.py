{
    'name': 'Point of Sale UX',
    'version': '16.0.1.0.0',
    'category': 'Point of Sale',
    'description': """
This module extend functionality of point of sale .
    """,
    'depends': [
        'l10n_ar_pos',
    ],
    'data': [
        'views/pos_session_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_ux/static/src/**/*'
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
