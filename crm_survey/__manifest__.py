{
    'name': "CRM recruitment interviews",
    'version': '1.0',
    'category': 'Human Resources Survey',
    'summary': 'Surveys',
    'description': """
        Use interview forms during recruitment process.
        This module is integrated with the survey module
        to allow you to define interviews.
    """,
    'depends': ['survey', 'crm'],
    'data': [
        'security/crm_recruitment_survey_security.xml',
        'security/ir.model.access.csv',
        'views/crm_job_views.xml',
        'views/crm_applicant_views.xml',
    ],
    'demo': [
        'data/hr_job_demo.xml',
    ],
    'auto_install': False,
}
 