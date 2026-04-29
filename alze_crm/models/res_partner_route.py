from odoo import models, fields, api
import re
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    route_id = fields.Many2one(
        'alze.route',
        string='Ruta',
        help="Selecciona la ruta a la que pertenece este contacto"
    )

    coord_input = fields.Char(
        string='Coordenadas',
        help="Pega aquí las coordenadas desde Google Maps (ej: '19.4326, -99.1332' o '19.4326 -99.1332')"
    )

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
                except ValueError:
                    pass

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

    # ----------------------------------------------------------------------
    # Sincronización Many2many de la ruta y propagación a leads
    # ----------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            partner._sync_partner_to_route()
            # La distribución automática se dispara al agregar el partner a la ruta
            if partner.route_id:
                partner.route_id._distribute_clients_auto()
        return partners

    def write(self, vals):
        old_routes = {p.id: p.route_id for p in self}
        res = super().write(vals)
        if any(f in vals for f in ['route_id', 'partner_latitude', 'partner_longitude', 'coord_input']):
            for partner in self:
                # Sincronizar Many2many de ruta
                new_route = partner.route_id
                old_route = old_routes.get(partner.id, False)
                if old_route != new_route:
                    if old_route:
                        old_route.write({'partner_ids': [(3, partner.id)]})
                        old_route._distribute_clients_auto()
                    if new_route:
                        new_route.write({'partner_ids': [(4, partner.id)]})
                        new_route._distribute_clients_auto()
                # Propagar a leads (evitando recursión)
                if not self.env.context.get('from_lead_write'):
                    partner.with_context(from_partner_write=True)._propagate_to_leads()
        return res

    def _sync_partner_to_route(self):
        for partner in self:
            if partner.route_id:
                if partner.id not in partner.route_id.partner_ids.ids:
                    partner.route_id.write({'partner_ids': [(4, partner.id)]})

    def _propagate_to_leads(self):
        """Propaga coordenadas y ruta a todos los leads donde este partner es cliente."""
        for partner in self:
            leads = self.env['crm.lead'].search([('partner_id', '=', partner.id)])
            if leads:
                update_vals = {
                    'coord_input': partner.coord_input,
                    'partner_latitude': partner.partner_latitude,
                    'partner_longitude': partner.partner_longitude,
                    'route_id': partner.route_id.id,
                }
                leads.with_context(from_partner_write=True).write(update_vals)