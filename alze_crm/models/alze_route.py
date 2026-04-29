from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import random
import requests
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class AlzeRoute(models.Model):
    _name = 'alze.route'
    _description = 'Ruta de CRM'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Nombre de la Ruta', required=True)
    code = fields.Char(string='Código', required=True, copy=False,
                       default=lambda self: self._generate_route_code())
    description = fields.Text(string='Descripción')
    active = fields.Boolean(string='Activo', default=True)
    color = fields.Integer(string='Color', default=0)

    polygon_coordinates = fields.Text(string='Coordenadas del Área')

    latitude_center = fields.Float(string='Latitud Central', compute='_compute_center', store=True)
    longitude_center = fields.Float(string='Longitud Central', compute='_compute_center', store=True)

    partner_ids = fields.Many2many('res.partner', string='Clientes Asignados')
    lead_ids = fields.One2many('crm.lead', 'route_id', string='Oportunidades')
    driver_ids = fields.Many2many('alze.driver', string='Choferes Asignados')
    schedule_ids = fields.One2many('alze.route.schedule', 'route_id', string='Días de Entrega')

    samsara_route_id = fields.Char(string='ID Ruta Samsara', help='Identificador de la ruta en Samsara')

    company_id = fields.Many2one('res.company', string='Compañía',
                                 default=lambda self: self.env.company)

    @api.model
    def _generate_route_code(self):
        last_route = self.search([], order='id desc', limit=1)
        if last_route and last_route.code and last_route.code.startswith('RUTA'):
            try:
                last_number = int(last_route.code[4:])
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
        return f'RUTA{new_number:04d}'

    @api.depends('polygon_coordinates')
    def _compute_center(self):
        for record in self:
            if record.polygon_coordinates:
                try:
                    coords = json.loads(record.polygon_coordinates)
                    if coords and len(coords) > 0:
                        lat_sum = sum(coord.get('lat', 0) for coord in coords)
                        lng_sum = sum(coord.get('lng', 0) for coord in coords)
                        count = len(coords)
                        record.latitude_center = lat_sum / count
                        record.longitude_center = lng_sum / count
                    else:
                        record.latitude_center = 0
                        record.longitude_center = 0
                except (json.JSONDecodeError, TypeError, AttributeError):
                    record.latitude_center = 0
                    record.longitude_center = 0
            else:
                record.latitude_center = 0
                record.longitude_center = 0

    @api.onchange('driver_ids')
    def _onchange_driver_ids(self):
        warning_msg = ""
        for driver in self.driver_ids:
            other_routes = driver.route_ids - self
            if other_routes:
                warning_msg += f"• {driver.name} ya está en: {', '.join(other_routes.mapped('name'))}\n"
        if warning_msg:
            return {
                'warning': {
                    'title': 'Choferes con rutas existentes',
                    'message': warning_msg,
                }
            }

    def get_partner_coordinates(self):
        self.ensure_one()
        partners = self.partner_ids.filtered(lambda p: p.partner_latitude and p.partner_longitude)
        return [{
            'lat': p.partner_latitude,
            'lng': p.partner_longitude,
            'name': p.display_name,
        } for p in partners]

    # ------------------------------------------------------------
    # Distribución automática de clientes (corregida para multi‑ruta)
    # ------------------------------------------------------------
    def _distribute_clients_auto(self):
        self.ensure_one()
        partners = self.partner_ids
        drivers = self.driver_ids

        # Si no hay clientes o choferes, retirar los clientes de esta ruta de todos los choferes
        if not partners or not drivers:
            for driver in drivers:
                # Solo quitar los clientes que pertenecen a esta ruta
                to_remove = driver.assigned_partner_ids & partners
                if to_remove:
                    driver.write({'assigned_partner_ids': [(3, pid) for pid in to_remove.ids]})
            return

        partner_list = list(partners)
        random.shuffle(partner_list)
        n = len(partner_list)
        m = len(drivers)
        base = n // m
        remainder = n % m

        # Para cada chofer, quitar solo sus clientes actuales que pertenecen a esta ruta
        for driver in drivers:
            current_route_partners = driver.assigned_partner_ids & partners
            if current_route_partners:
                driver.write({'assigned_partner_ids': [(3, pid) for pid in current_route_partners.ids]})

        # Asignar la nueva distribución
        start = 0
        for i, driver in enumerate(drivers):
            size = base + (1 if i < remainder else 0)
            new_partner_ids = [p.id for p in partner_list[start:start+size]]
            if new_partner_ids:
                driver.write({'assigned_partner_ids': [(4, pid) for pid in new_partner_ids]})
            start += size

        # Actualizar los leads de esta ruta para que reflejen el nuevo chofer
        leads = self.env['crm.lead'].search([('route_id', '=', self.id)])
        for lead in leads:
            lead._assign_driver_and_schedule()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._distribute_clients_auto()
        return records

    def write(self, vals):
        old_driver_ids = {rec.id: rec.driver_ids.ids for rec in self}
        res = super().write(vals)
        if any(f in vals for f in ['partner_ids', 'driver_ids']):
            for record in self:
                if 'driver_ids' in vals:
                    old_drivers = self.env['alze.driver'].browse(old_driver_ids.get(record.id, []))
                    new_drivers = record.driver_ids
                    removed_drivers = old_drivers - new_drivers
                    # Al quitar un chofer, solo retirar los clientes de esta ruta
                    for driver in removed_drivers:
                        to_remove = driver.assigned_partner_ids & record.partner_ids
                        if to_remove:
                            driver.write({'assigned_partner_ids': [(3, pid) for pid in to_remove.ids]})
                record._distribute_clients_auto()
        return res

    # ------------------------------------------------------------
    # Próxima fecha de entrega según horarios
    # ------------------------------------------------------------
    def _get_next_schedule_date(self):
        self.ensure_one()
        schedules = self.schedule_ids
        if not schedules:
            return False

        today = datetime.now().date()
        for days_ahead in range(0, 7):
            check_date = today + timedelta(days=days_ahead)
            weekday = str(check_date.weekday())
            day_schedules = schedules.filtered(lambda s: s.day_of_week == weekday)
            if day_schedules:
                earliest = day_schedules.sorted('start_time')[0]
                start_hour = int(earliest.start_time)
                start_minute = int((earliest.start_time % 1) * 60)
                scheduled_dt = datetime.combine(check_date, datetime.min.time()).replace(hour=start_hour, minute=start_minute)
                return scheduled_dt
        return False

    # ------------------------------------------------------------
    # ENVÍO DE RUTA A SAMSARA (mantenido por si se usa el botón en la ruta)
    # ------------------------------------------------------------
    def action_send_route_to_samsara(self):
        self.ensure_one()
        token = self.env['ir.config_parameter'].sudo().get_param('samsara_api_token')
        if not token:
            raise UserError(_('Token de Samsara no configurado.'))

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 1. Validaciones
        if not self.partner_ids:
            raise UserError(_('La ruta no tiene clientes asignados.'))
        drivers = self.driver_ids.filtered(lambda d: d.samsara_driver_id)
        if not drivers:
            raise UserError(_('Ningún chofer de la ruta tiene ID de Samsara. Envíe los choferes primero.'))
        if not self.schedule_ids:
            raise UserError(_('La ruta no tiene horarios de entrega configurados.'))

        driver = drivers[0]
        driver_samsara_id = driver.samsara_driver_id

        # 2. Crear o buscar direcciones de clientes
        address_ids = []
        for partner in self.partner_ids:
            addr_name = partner.display_name
            search_url = "https://api.samsara.com/addresses"
            search_resp = requests.get(search_url, headers=headers)
            addr_id = None
            if search_resp.status_code == 200:
                try:
                    addresses = search_resp.json().get("data", [])
                except Exception:
                    _logger.warning("Error al interpretar la lista de direcciones de Samsara")
                    addresses = []
                for a in addresses:
                    if a.get("name", "").strip().lower() == addr_name.strip().lower():
                        addr_id = a["id"]
                        break
            else:
                _logger.warning("Error al buscar direcciones en Samsara: %s", search_resp.text)

            if not addr_id:
                body = {
                    "name": addr_name,
                    "formattedAddress": f"{partner.street or ''}, {partner.city or ''}",
                    "geofence": {"circle": {"radiusMeters": 250}}
                }
                create_resp = requests.post("https://api.samsara.com/addresses", headers=headers, json=body)
                if create_resp.status_code == 200:
                    try:
                        addr_id = create_resp.json()["data"]["id"]
                    except Exception:
                        _logger.error("No se pudo extraer ID de dirección creada. Respuesta: %s", create_resp.text)
                        continue
                else:
                    _logger.warning("Error creando dirección para %s: %s", addr_name, create_resp.text)
                    continue

            address_ids.append(addr_id)

        if not address_ids:
            raise UserError(_('No se pudo crear ninguna dirección de cliente en Samsara.'))

        # 3. Calcular horarios programados
        next_date = self._get_next_schedule_date()
        if not next_date:
            raise UserError(_('No se pudo determinar una fecha de entrega programada.'))

        stops = []
        for i, addr_id in enumerate(address_ids):
            stop_data = {
                "addressId": addr_id,
                "notes": f"Cliente: {self.partner_ids[i].display_name}"
            }
            if i == 0:
                stop_data["scheduledDepartureTime"] = (next_date + timedelta(hours=i)).isoformat() + "Z"
            elif i == len(address_ids) - 1:
                stop_data["scheduledArrivalTime"] = (next_date + timedelta(hours=i)).isoformat() + "Z"
            else:
                stop_data["scheduledArrivalTime"] = (next_date + timedelta(hours=i)).isoformat() + "Z"
                stop_data["scheduledDepartureTime"] = (next_date + timedelta(hours=i, minutes=30)).isoformat() + "Z"
            stops.append(stop_data)

        # 4. Crear la ruta en Samsara
        create_route_url = "https://api.samsara.com/fleet/routes"
        route_body = {
            "name": f"{self.name} - {next_date.strftime('%d/%m/%Y')}",
            "driverId": driver_samsara_id,
            "stops": stops,
            "settings": {"optimize": "distance"}
        }

        route_resp = requests.post(create_route_url, headers=headers, json=route_body)
        if route_resp.status_code == 200:
            try:
                samsara_route_id = route_resp.json()["data"]["id"]
            except Exception as e:
                _logger.error("Error al leer la respuesta de creación de ruta: %s", route_resp.text)
                raise UserError(_('La ruta se creó en Samsara, pero no se pudo obtener el ID. Verifique manualmente.'))
            self.write({'samsara_route_id': samsara_route_id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Samsara',
                    'message': _('Ruta enviada a Samsara (ID: %s)') % samsara_route_id,
                    'type': 'success',
                }
            }
        else:
            _logger.error("Error al crear ruta en Samsara. Status: %s, Respuesta: %s", route_resp.status_code, route_resp.text)
            try:
                error_info = route_resp.json()
                error_msg = error_info.get("message", route_resp.text)
            except Exception:
                error_msg = route_resp.text
            raise UserError(_('Error al crear ruta en Samsara:\n%s') % error_msg)