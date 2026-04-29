# -*- coding: utf-8 -*-

from odoo import fields, http, _
from odoo.http import request


class HrAttendance(http.Controller):
    @http.route('/employee/images', type="json", auth="public")
    def get_employee_images(self, employee_id=None):
        if employee_id:
            employees = request.env['hr.employee'].sudo().search([('id', '=', employee_id)])
            for employee in employees:
                employee_data = [{"employee_id": employee.id, "image": employee.image_1920, "name": employee.name}]
                return employee_data
        else:
            employees = request.env['hr.employee'].sudo().search([])
            employee_data = []
            for employee in employees:
                employee_data.append({"employee_id": employee.id, "image":employee.image_1920, "name": employee.name})
            return employee_data

    @http.route('/hr_attendance/check_duplicate', type='json', auth='public')
    def check_duplicate(self, employee_id):
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee.exists():
            return {'error': 'Empleado no encontrado'}

        last_attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee_id)
        ], order='create_date desc', limit=1)

        if last_attendance:
            last_time = last_attendance.create_date
            now = fields.Datetime.now()
            diff_seconds = (now - last_time).total_seconds()
            wait_seconds = 90
            if diff_seconds < wait_seconds:
                return {
                    'blocked': True,
                    'message': f'Ya se registró recientemente. Espere {int(wait_seconds - diff_seconds)} segundos.',
                    'wait': wait_seconds - int(diff_seconds)
                }
        return {'blocked': False}