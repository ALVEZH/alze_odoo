from odoo import models, fields, api
import re
import json
import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    coord_input = fields.Char(string='Coordenadas')
    route_id = fields.Many2one('alze.route', string='Ruta')
    partner_latitude = fields.Float(digits=(16, 6))
    partner_longitude = fields.Float(digits=(16, 6))

    route_driver_ids = fields.Many2many(
        'alze.driver',
        string='Choferes de la Ruta',
        compute='_compute_route_drivers',
        readonly=True,
        store=False,
    )

    @api.depends('route_id')
    def _compute_route_drivers(self):
        for lead in self:
            if lead.route_id:
                lead.route_driver_ids = lead.route_id.driver_ids
            else:
                lead.route_driver_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_id = vals.get('partner_id')
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                if partner.exists():
                    vals.setdefault('coord_input', partner.coord_input)
                    vals.setdefault('partner_latitude', partner.partner_latitude)
                    vals.setdefault('partner_longitude', partner.partner_longitude)
                    vals.setdefault('route_id', partner.route_id.id)
        leads = super().create(vals_list)
        return leads

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            p = self.partner_id
            self.coord_input = p.coord_input
            self.partner_latitude = p.partner_latitude
            self.partner_longitude = p.partner_longitude
            self.route_id = p.route_id
        else:
            self.coord_input = False
            self.partner_latitude = False
            self.partner_longitude = False
            self.route_id = False

    @api.onchange('coord_input')
    def _onchange_coord_input(self):
        if self.coord_input:
            match = re.search(r'([-+]?\d+\.?\d*)\s*[,\s]\s*([-+]?\d+\.?\d*)', self.coord_input.strip())
            if match:
                try:
                    lat = float(match.group(1))
                    lng = float(match.group(2))
                    self.partner_latitude = lat
                    self.partner_longitude = lng
                    self._compute_route_from_coords()
                except ValueError:
                    pass

    def _compute_route_from_coords(self):
        if not self.partner_latitude or not self.partner_longitude:
            self.route_id = False
            return
        Route = self.env.get('alze.route')
        if not Route:
            self.route_id = False
            return
        all_routes = Route.search([
            ('active', '=', True),
            ('polygon_coordinates', '!=', False)
        ])
        lat = self.partner_latitude
        lng = self.partner_longitude
        matched = False
        for route in all_routes:
            try:
                coords = json.loads(route.polygon_coordinates)
                if len(coords) < 3:
                    continue
                poly = [(c['lng'], c['lat']) for c in coords]
                if self._point_in_polygon(lng, lat, poly):
                    matched = route
                    break
            except Exception as e:
                _logger.warning("Error procesando ruta %s: %s", route.name, e)
                continue
        self.route_id = matched

    def _point_in_polygon(self, lng, lat, poly):
        x, y = lng, lat
        n = len(poly)
        inside = False
        p1x, p1y = poly[0]
        for i in range(n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def action_open_google_maps(self):
        self.ensure_one()
        if self.partner_latitude and self.partner_longitude:
            url = f"https://www.google.com/maps?q={self.partner_latitude},{self.partner_longitude}"
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }

    def open_route_form(self):
        self.ensure_one()
        if self.route_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'alze.route',
                'res_id': self.route_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['coord_input', 'partner_latitude', 'partner_longitude', 'route_id']):
            if not self.env.context.get('from_partner_write'):
                for lead in self:
                    if lead.partner_id:
                        update_vals = {}
                        if 'coord_input' in vals and lead.coord_input != lead.partner_id.coord_input:
                            update_vals['coord_input'] = lead.coord_input
                        if 'partner_latitude' in vals and lead.partner_latitude != lead.partner_id.partner_latitude:
                            update_vals['partner_latitude'] = lead.partner_latitude
                        if 'partner_longitude' in vals and lead.partner_longitude != lead.partner_id.partner_longitude:
                            update_vals['partner_longitude'] = lead.partner_longitude
                        if 'route_id' in vals and lead.route_id != lead.partner_id.route_id:
                            update_vals['route_id'] = lead.route_id.id
                        if update_vals:
                            lead.partner_id.with_context(from_lead_write=True).write(update_vals)
        return res