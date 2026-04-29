from odoo import models, fields, api, _

class AlzeSede(models.Model):
    _name = 'alze.sede'
    _description = 'Sede (ubicación física)'
    _order = 'name'

    name = fields.Char(string='Nombre de la sede', required=True)
    street = fields.Char(string='Calle y número')
    street2 = fields.Char(string='Colonia / Barrio')
    city = fields.Char(string='Ciudad')
    zip = fields.Char(string='Código postal')
    country_id = fields.Many2one('res.country', string='País')
    phone = fields.Char(string='Teléfono')
    email = fields.Char(string='Correo electrónico')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    
    # Nuevo campo unificado para coordenadas
    coordinates = fields.Char(
        string='Coordenadas (latitud, longitud)',
        help='Ejemplo: 19.432608, -99.133209\n'
             'Cómo obtenerlas: haz clic derecho en el lugar exacto del mapa en Google Maps, selecciona "¿Qué hay aquí?" y copia las coordenadas que aparecen.'
    )
    
    full_address = fields.Char(string='Dirección completa', compute='_compute_full_address')

    @api.depends('street', 'street2', 'city', 'zip', 'country_id')
    def _compute_full_address(self):
        for sede in self:
            parts = []
            if sede.street:
                parts.append(sede.street)
            if sede.street2:
                parts.append(sede.street2)
            if sede.city:
                parts.append(sede.city)
            if sede.zip:
                parts.append(sede.zip)
            if sede.country_id:
                parts.append(sede.country_id.name)
            sede.full_address = ', '.join(parts)

    def action_open_google_maps(self):
        self.ensure_one()
        import re
        # Intentar extraer latitud y longitud del campo coordinates
        lat = lon = None
        if self.coordinates:
            # Buscar patrones de números decimales (pueden tener signo negativo)
            numbers = re.findall(r'-?\d+\.?\d*', self.coordinates)
            if len(numbers) >= 2:
                try:
                    lat = float(numbers[0])
                    lon = float(numbers[1])
                except ValueError:
                    pass
        if lat is not None and lon is not None:
            url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        elif self.full_address:
            import urllib.parse
            address = urllib.parse.quote(self.full_address)
            url = f"https://www.google.com/maps/search/?api=1&query={address}"
        else:
            raise Warning(_('No hay dirección ni coordenadas definidas para esta sede.'))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }