from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests

class AlzeSamsaraRoute(models.Model):
    _name = 'alze.samsara.route'
    _description = 'Ruta en Samsara'
    _order = 'date desc, driver_id'

    name = fields.Char(string='Nombre', required=True, tracking=True)
    samsara_route_id = fields.Char(string='ID Ruta Samsara', required=True, index=True)
    driver_id = fields.Many2one('alze.driver', string='Conductor', required=True)
    date = fields.Date(string='Fecha', required=True)
    lead_ids = fields.One2many('crm.lead', 'samsara_route_id', string='Leads')
    state = fields.Selection([
        ('active', 'Activa'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ], default='active', string='Estado', tracking=True)

    def _get_samsara_headers(self):
        token = self.env['ir.config_parameter'].sudo().get_param('samsara_api_token')
        if not token:
            raise UserError(_('Token de Samsara no configurado.'))
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def write(self, vals):
        res = super().write(vals)
        for route in self:
            if not route.samsara_route_id:
                continue
            headers = self._get_samsara_headers()
            samsara_vals = {}
            if 'name' in vals:
                samsara_vals['name'] = vals['name']
            if 'state' in vals:
                # Mapear estado de Odoo a Samsara
                if vals['state'] == 'completed':
                    samsara_vals['state'] = 'completed'
                elif vals['state'] == 'cancelled':
                    samsara_vals['state'] = 'cancelled'
                elif vals['state'] == 'active':
                    samsara_vals['state'] = 'active'
            if samsara_vals:
                url = f"https://api.samsara.com/fleet/routes/{route.samsara_route_id}"
                resp = requests.patch(url, headers=headers, json=samsara_vals)
                if resp.status_code not in (200, 201):
                    _logger.warning("Error al actualizar ruta %s en Samsara: %s", route.name, resp.text)
        return res

    def unlink(self):
        for route in self:
            if route.samsara_route_id:
                headers = self._get_samsara_headers()
                url = f"https://api.samsara.com/fleet/routes/{route.samsara_route_id}"
                requests.delete(url, headers=headers)
            route.lead_ids.write({'samsara_route_id': False, 'samsara_stop_id': False})
        return super().unlink()

    def action_complete_route(self):
        self.ensure_one()
        self.state = 'completed'

    def action_cancel_route(self):
        self.ensure_one()
        self.state = 'cancelled'