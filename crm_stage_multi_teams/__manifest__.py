# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
<<<<<<< HEAD:crm_stage_multi_teams/__manifest__.py
    'name': 'CRM Stage Multi Teams',
    'version': "18.0.1.0.0",
||||||| parent of 13273116 (temp):crm_teams_ux/__manifest__.py
    'name': 'CRM Teams UX',
    'version': "17.0.1.0.0",
=======
    'name': 'CRM Teams UX',
    'version': "17.0.1.1.0",
>>>>>>> 13273116 (temp):crm_teams_ux/__manifest__.py
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'crm',
    ],
    'data': [
        'views/crm_stage_views.xml',
        'views/crm_lead_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': 'post_init_hook',
}
