{
    'name': 'Point of Sale UX',
<<<<<<< HEAD
    'version': "18.0.1.0.0",
||||||| parent of 84c0fab7 (temp)
    'version': "17.0.1.0.0",
=======
    'version': "17.0.1.1.0",
>>>>>>> 84c0fab7 (temp)
    'category': 'Point of Sale',
    'description': """
This module extend functionality of point of sale .
    """,
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/pos_session_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_ux/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
