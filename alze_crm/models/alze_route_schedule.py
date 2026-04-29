from odoo import models, fields

class AlzeRouteSchedule(models.Model):
    _name = 'alze.route.schedule'
    _description = 'Horario de Entrega de Ruta'
    _order = 'day_of_week, start_time'

    route_id = fields.Many2one('alze.route', string='Ruta', required=True, ondelete='cascade')
    day_of_week = fields.Selection([
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo'),
    ], string='Día', required=True)
    start_time = fields.Float(string='Hora de Inicio', required=True, default=8.0,
                              help='Hora de inicio en formato decimal. Ej: 8.0 = 08:00, 9.5 = 09:30')
    end_time = fields.Float(string='Hora de Fin', required=True, default=17.0,
                            help='Hora de fin en formato decimal. Ej: 17.0 = 17:00')
    
    _sql_constraints = [
        ('unique_day_per_route', 'unique(route_id, day_of_week)',
         'Ya existe un horario para ese día en esta ruta.')
    ]