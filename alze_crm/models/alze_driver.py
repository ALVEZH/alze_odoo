from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import requests
import logging

_logger = logging.getLogger(__name__)

class AlzeDriver(models.Model):
    _name = 'alze.driver'
    _description = 'Chofer / Transportista'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Nombre completo', required=True)
    driver_id_number = fields.Char(string='N° Licencia / ID')
    phone = fields.Char(string='Teléfono')
    mobile = fields.Char(string='Móvil')
    email = fields.Char(string='Correo electrónico')

    street = fields.Char(string='Calle')
    street2 = fields.Char(string='Calle 2')
    city = fields.Char(string='Ciudad')
    state_id = fields.Many2one('res.country.state', string='Estado')
    zip = fields.Char(string='Código Postal')
    country_id = fields.Many2one('res.country', string='País')

    active = fields.Boolean(string='Activo', default=True)
    notes = fields.Text(string='Notas internas')

    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    driver_image = fields.Image(string='Foto del Chofer', max_width=1024, max_height=1024)

    employee_id = fields.Many2one('hr.employee', string='Empleado Vinculado', ondelete='set null')

    samsara_driver_id = fields.Char(string='ID Samsara', help='Identificador único del conductor en Samsara')

    vehicle_assigned_ids = fields.Many2many('alze.driver.vehicle', string='Vehículos Asignados',
                                            compute='_compute_vehicle_assigned_ids', inverse='_set_vehicle_assigned_ids',
                                            store=True,
                                            domain="[('active', '=', True)]",
                                            help="Selecciona los vehículos que usará este chofer.")
    vehicle_ids = fields.One2many('alze.driver.vehicle', 'current_driver_id', string='Vehículos (One2many)')
    vehicle_count = fields.Integer(string='N° Vehículos', compute='_compute_vehicle_count')
    vehicle_summary_json = fields.Text(string='Resumen de Vehículos (JSON)', compute='_compute_vehicle_summary_json')

    route_ids = fields.Many2many('alze.route', string='Rutas Asignadas', readonly=True)
    route_names = fields.Char(string='Nombres de Rutas', compute='_compute_route_names', store=True)
    route_colors_json = fields.Text(string='Datos de Rutas (JSON)', compute='_compute_route_colors_json')

    assigned_partner_ids = fields.Many2many('res.partner', string='Clientes Asignados')

    @api.depends('vehicle_assigned_ids')
    def _compute_vehicle_count(self):
        for driver in self:
            driver.vehicle_count = len(driver.vehicle_assigned_ids)

    @api.depends('vehicle_assigned_ids', 'vehicle_assigned_ids.plate', 'vehicle_assigned_ids.image', 'vehicle_assigned_ids.active')
    def _compute_vehicle_summary_json(self):
        for driver in self:
            active_vehicles = driver.vehicle_assigned_ids.filtered(lambda v: v.active)
            count = len(active_vehicles)
            data = {
                'count': count,
                'single_plate': active_vehicles[0].plate if count == 1 else False,
                'first_vehicle_id': active_vehicles[0].id if count >= 1 else False,
            }
            driver.vehicle_summary_json = json.dumps(data)

    @api.depends('vehicle_ids')
    def _compute_vehicle_assigned_ids(self):
        for driver in self:
            driver.vehicle_assigned_ids = driver.vehicle_ids

    def _set_vehicle_assigned_ids(self):
        for driver in self:
            current_vehicles = driver.vehicle_ids
            selected_vehicles = driver.vehicle_assigned_ids

            to_add = selected_vehicles - current_vehicles
            to_remove = current_vehicles - selected_vehicles

            for vehicle in to_remove:
                vehicle.write({'current_driver_id': False})

            for vehicle in to_add:
                if vehicle.current_driver_id and vehicle.current_driver_id != driver:
                    continue
                vehicle.write({'current_driver_id': driver.id})

    @api.depends('route_ids', 'route_ids.name')
    def _compute_route_names(self):
        for driver in self:
            names = driver.route_ids.mapped('name')
            driver.route_names = ', '.join(names) if names else 'Ninguna'

    @api.depends('route_ids', 'route_ids.color', 'route_ids.name')
    def _compute_route_colors_json(self):
        for driver in self:
            data = []
            for route in driver.route_ids:
                data.append({
                    'color_index': route.color or 0,
                    'name': route.name,
                })
            driver.route_colors_json = json.dumps(data)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id') and not vals.get('name'):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                if employee:
                    vals.setdefault('name', employee.name)
                    vals.setdefault('phone', employee.work_phone or employee.mobile_phone)
                    vals.setdefault('mobile', employee.mobile_phone)
                    vals.setdefault('email', employee.work_email)
                    vals.setdefault('driver_image', employee.image_1920)
                    if employee.address_id:
                        addr = employee.address_id
                        vals.setdefault('street', addr.street)
                        vals.setdefault('street2', addr.street2)
                        vals.setdefault('city', addr.city)
                        vals.setdefault('state_id', addr.state_id.id)
                        vals.setdefault('zip', addr.zip)
                        vals.setdefault('country_id', addr.country_id.id)
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            emp = self.employee_id
            if not self.name:
                self.name = emp.name
            if not self.phone:
                self.phone = emp.work_phone or emp.mobile_phone
            if not self.mobile:
                self.mobile = emp.mobile_phone
            if not self.email:
                self.email = emp.work_email
            if not self.driver_image:
                self.driver_image = emp.image_1920
            if emp.address_id and not any([self.street, self.city]):
                addr = emp.address_id
                self.street = addr.street
                self.street2 = addr.street2
                self.city = addr.city
                self.state_id = addr.state_id
                self.zip = addr.zip
                self.country_id = addr.country_id

    def action_send_to_samsara(self):
        self.ensure_one()
        token = self.env['ir.config_parameter'].sudo().get_param('samsara_api_token')
        if not token:
            raise UserError(_('No está configurado el token de Samsara. Contacte al administrador.'))

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 1. Buscar conductor por nombre exacto (ignorando mayúsculas/minúsculas y espacios)
        search_url = "https://api.samsara.com/fleet/drivers"
        response = requests.get(search_url, headers=headers)
        driver_id = None
        if response.status_code == 200:
            drivers = response.json().get("data", [])
            for d in drivers:
                if d['name'].strip().lower() == self.name.strip().lower():
                    driver_id = d['id']
                    break
        else:
            _logger.warning("Error al buscar conductores en Samsara: %s", response.text)

        if driver_id:
            self.write({'samsara_driver_id': driver_id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                 'title': 'Samsara',
                    'message': _('El conductor ya existe en Samsara (ID: %s).') % driver_id,
                    'type': 'info',
                }
            }

        # 2. No existe, crearlo (ahora con password)
        create_url = "https://api.samsara.com/fleet/drivers"
        username = f"odoo_{self.id}"
        body = {
            "name": self.name,
            "username": username,
            "password": "OdooDriver2024!",  # <-- Password requerido por Samsara
            "externalIds": {"odooId": str(self.id)}
        }
        create_response = requests.post(create_url, headers=headers, json=body)
        if create_response.status_code == 200:
            driver_data = create_response.json()["data"]
            driver_id = driver_data["id"]
            self.write({'samsara_driver_id': driver_id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Samsara',
                    'message': _('Conductor creado en Samsara (ID: %s)') % driver_id,
                    'type': 'success',
                }
            }
        else:
            error_msg = create_response.json().get("message", create_response.text)
            raise UserError(_('Error al crear conductor en Samsara: %s') % error_msg)