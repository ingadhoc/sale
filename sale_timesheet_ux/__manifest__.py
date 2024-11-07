{
    "name": "Sales Timesheet UX",
    "summary": "",
    "version": "18.0.1.0.0",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "author": "ADHOC SA",
    "category": "sale",
    "depends": [
        "sale_timesheet",
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/project_inherit.xml',
        "wizards/res_config_settings_views.xml",
        "wizards/project_change_biillable_views.xml",
    ],
    "demo": [
    ],
    "application": False,
    'installable': True,
}
