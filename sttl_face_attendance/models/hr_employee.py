# -*- coding: utf-8 -*-

from odoo import models
from odoo import fields  # si no está importado, agrégalo al inicio del archivo
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class Employee(models.Model):
    _inherit = 'hr.employee'

    def new_employee_image(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'new_employee_image',
            'params': {
                'employee_id': self.id,
            }
        }
        
    def create_employee_from_kiosk(self, vals):
        try:
            employee = self.sudo().create({
                'name': vals['name'],
                'image_1920': vals['image'],
            })
            return employee.id
        except Exception as e:
            _logger.error("Error creating employee from kiosk: %s", e)
            return False

    def register_face(self, image_data):
        try:
            if image_data.startswith('data:image/png;base64,'):
                image_data = image_data.split('base64,')[1]
            if image_data:
                self.image_1920 = image_data
                _logger.info("Image saved successfully.")
            else:
                _logger.warning("No image data provided.")
        except Exception as e:
            _logger.error("Error registering face: %s", str(e))
            
    def attendance_with_anti_duplicate(self, employee_id, continuous_mode=False):
        """
        Registra la asistencia con validación anti-duplicado por tiempo.
        Si el empleado ya registró en los últimos 90 segundos, devuelve un bloqueo.
        """
        employee = self.browse(employee_id)
        if not employee.exists():
            return {'error': 'Empleado no encontrado'}

        # Buscar la última asistencia del empleado
        last_attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', employee_id)
        ], order='create_date desc', limit=1)

        if last_attendance:
            last_time = last_attendance.create_date
            now = fields.Datetime.now()
            diff_seconds = (now - last_time).total_seconds()
            wait_seconds = 90  # tiempo de espera en segundos
            if diff_seconds < wait_seconds:
                return {
                    'blocked': True,
                    'message': f'Ya se registró recientemente. Espere {int(wait_seconds - diff_seconds)} segundos.',
                    'wait': wait_seconds - int(diff_seconds)
                }

        # Si pasa la validación, proceder con la marcación normal
        attendance_data = employee._attendance_action_change()
        return {
            'attendance': attendance_data,
            'employee': {'id': employee.id, 'name': employee.name}
        }