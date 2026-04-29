{
    'name': 'Gestión Integral de RH (Sedes y Salarios)',
    'version': '1.2',
    'summary': 'Control de rangos salariales por puesto y catálogo extendido de sedes.',
    'category': 'Human Resources',
    'author': 'Alan UAA',
    'depends': ['hr', 'hr_contract', 'base_geolocalize'],  # base_geolocalize es opcional
    'data': [
        'security/ir.model.access.csv',
        'views/hr_job_views.xml',
        'views/hr_contract_views.xml',
        'views/alze_sede_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_department_views.xml',
        'views/menu_views.xml',
        'views/hr_work_location_hide.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'alze_hr_core/static/src/js/save_button.js',
            
            'alze_hr_core/static/src/js/salary_alert.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}