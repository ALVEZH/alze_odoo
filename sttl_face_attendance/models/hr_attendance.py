# models/hr_attendance.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import math

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    sede_id = fields.Many2one(
        'alze.sede',
        string='Sede',
        compute='_compute_sede_from_coordinates',
        store=True,
        help='Sede más cercana a las coordenadas GPS del registro'
    )

    @api.depends('check_in', 'check_out')
    def _compute_sede_from_coordinates(self):
        """Calcula la sede más cercana usando las coordenadas guardadas en la asistencia."""
        # Obtener todas las sedes activas
        sedes = self.env['alze.sede'].search([])
        if not sedes:
            return

        for attendance in self:
            # Obtener coordenadas del registro (asumiendo que las tienes en campos separados)
            # Nota: Dependiendo de tu versión de Odoo, las coordenadas pueden estar en un campo
            # 'latitude' y 'longitude' o en un campo 'coordinates' como texto.
            # Ajusta según tu modelo. Supongamos que tienes campos 'latitude' y 'longitude'.
            lat = getattr(attendance, 'latitude', None)
            lon = getattr(attendance, 'longitude', None)
            if not lat or not lon:
                # Si no hay coordenadas, intentar extraer del campo 'coordinates' (si existe)
                # Algunas personalizaciones guardan un string "lat,lng"
                coord_str = getattr(attendance, 'coordinates', '')
                if coord_str and ',' in coord_str:
                    parts = coord_str.split(',')
                    try:
                        lat = float(parts[0].strip())
                        lon = float(parts[1].strip())
                    except ValueError:
                        pass
            if lat is None or lon is None:
                attendance.sede_id = False
                continue

            # Calcular la sede más cercana
            closest_sede = None
            min_distance = float('inf')
            for sede in sedes:
                if not sede.coordinates:
                    continue
                # Extraer coordenadas de la sede
                try:
                    coord_parts = sede.coordinates.split(',')
                    sede_lat = float(coord_parts[0].strip())
                    sede_lon = float(coord_parts[1].strip())
                except (ValueError, IndexError):
                    continue
                # Calcular distancia Haversine (en km)
                distance = self._haversine_distance(lat, lon, sede_lat, sede_lon)
                if distance < min_distance:
                    min_distance = distance
                    closest_sede = sede
            attendance.sede_id = closest_sede.id if closest_sede else False

    @staticmethod
    def _haversine_distance(lat1, lon1, lat2, lon2):
        """Calcula la distancia en kilómetros entre dos puntos geográficos."""
        R = 6371  # Radio de la Tierra en km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    _inherit = 'hr.attendance'

    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))
    coordinates = fields.Char(string='Coordenadas (lat, lon)', compute='_compute_coordinates', store=False)

    @api.depends('latitude', 'longitude')
    def _compute_coordinates(self):
        for rec in self:
            if rec.latitude is not None and rec.longitude is not None:
                rec.coordinates = f"{rec.latitude}, {rec.longitude}"
            else:
                rec.coordinates = False