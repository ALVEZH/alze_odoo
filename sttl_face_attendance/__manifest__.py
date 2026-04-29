# -*- coding: utf-8 -*-

{
    'name': 'Reconocimiento Facial para Asistencia de RRHH',
    'version': '17.0.2.0',
    'summary': 'Reconocimiento Facial para Asistencia de RRHH',
    'category': 'Human Resources',
    'depends': ['hr_attendance', 'hr'],
    'description':
    '''
        Módulo de Odoo para el reconocimiento facial en la asistencia de recursos humanos. 
        Permite a los empleados registrarse utilizando su rostro, mejorando la precisión y eficiencia del sistema de asistencia, 
        evitando suplantación de identidad y confirmación de personal existente. 
    '''
,    'data': [
        'views/employee.xml',
    ],
    "author": "Alan UAA",
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'sttl_face_attendance/static/src/xml/capture_employee_image.xml',

            'sttl_face_attendance/static/src/css/style.css',

            'sttl_face_attendance/static/face-api/dist/face-api.js',
            'sttl_face_attendance/static/src/js/capture_employee_image.js',
        ],
        'hr_attendance.assets_public_attendance': [
            'sttl_face_attendance/static/src/xml/public_kiosk_app.xml',
            'sttl_face_attendance/static/src/css/style.css',
            'sttl_face_attendance/static/face-api/dist/face-api.js',
            'sttl_face_attendance/static/src/js/public_kiosk_app.js',
        ]
    },
    'installable': True,
    'application': False,
}
