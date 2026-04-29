from odoo import models, fields

class AlzeStartPoint(models.Model):
    _name = 'alze.start.point'
    _description = 'Punto de Partida para Samsara'
    _rec_name = 'name'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    street = fields.Char(string='Calle')
    street2 = fields.Char(string='Calle 2')
    city = fields.Char(string='Ciudad')
    state_id = fields.Many2one('res.country.state', string='Estado')
    zip = fields.Char(string='C.P.')
    country_id = fields.Many2one('res.country', string='País')
    partner_latitude = fields.Float(string='Latitud', required=True, digits=(16, 6))
    partner_longitude = fields.Float(string='Longitud', required=True, digits=(16, 6))
    radius_meters = fields.Integer(string='Radio (metros)', default=250)
    start_time = fields.Float(string='Hora de inicio', default=8.0,
                              help='Hora local de salida del punto de partida (formato 24h).')
    sequence = fields.Integer(string='Secuencia', default=10)