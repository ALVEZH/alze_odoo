from odoo import models, fields

class AlzeDriverVehicle(models.Model):
    _name = 'alze.driver.vehicle'
    _description = 'Vehículo'
    _rec_name = 'plate'
    _order = 'plate'

    brand = fields.Char(string='Marca')
    model = fields.Char(string='Modelo')
    plate = fields.Char(string='Placas', required=True)
    image = fields.Image(string='Foto', max_width=1024, max_height=1024)
    active = fields.Boolean(string='Activo', default=True)
    
    # Relación con el chofer actual (único)
    current_driver_id = fields.Many2one('alze.driver', string='Chofer Asignado', index=True,
                                        help='Vehículo asignado actualmente a este chofer.')

    _sql_constraints = [
        ('unique_plate', 'unique(plate)', 'Ya existe un vehículo con esa placa.'),
    ]