from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import requests
from datetime import datetime, timedelta, date, time
import pytz

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    product_variant_id = fields.Many2one('alze.product.variant', string='Producto')
    order_quantity = fields.Float(string='Cantidad', default=1.0)
    order_presentation = fields.Selection([
        ('box', 'Caja'),
        ('cono', 'Cono (30 pzas)'),
        ('piece', 'Pieza'),
        ('dozen', 'Docenero (12 pzas)'),
        ('kilo', 'Kilo'),
    ], string='Presentación', default='box')

    order_total_weight = fields.Float(string='Peso Total (kg)', compute='_compute_order_weight', store=True)

    delivery_type = fields.Selection([
        ('puerta', 'Puerta'),
        ('ruta', 'Ruta'),
    ], string='Tipo de Entrega', default='ruta', required=True)

    order_display = fields.Char(string='Pedido', compute='_compute_order_display', store=True)
    order_breakdown = fields.Char(string='Desglose', compute='_compute_order_breakdown', store=True)
    is_kilo = fields.Boolean(string='Es Kilo', compute='_compute_is_kilo', store=True)

    assigned_driver_id = fields.Many2one('alze.driver', string='Chofer Asignado', readonly=True)
    scheduled_date = fields.Date(string='Fecha de Entrega Programada')
    start_point_id = fields.Many2one('alze.start.point', string='Punto de Partida',
                                     help="Selecciona el punto de partida para esta entrega. Si no se elige, se usará el primero en orden.")

    samsara_stop_id = fields.Char(string='ID Parada Samsara', readonly=True)
    samsara_route_id = fields.Many2one('alze.samsara.route', string='Ruta Samsara', readonly=True)

    @api.depends('product_variant_id', 'order_quantity', 'order_presentation')
    def _compute_order_weight(self):
        for lead in self:
            weight = 0.0
            if lead.product_variant_id and lead.order_quantity > 0:
                variant = lead.product_variant_id
                try:
                    box_kg = float(variant.weight)
                except ValueError:
                    box_kg = 0.0
                pieces = variant.pieces_per_box or 360
                if pieces > 0:
                    per_piece = box_kg / pieces
                    if lead.order_presentation == 'box':
                        weight = box_kg * lead.order_quantity
                    elif lead.order_presentation == 'cono':
                        weight = per_piece * 30 * lead.order_quantity
                    elif lead.order_presentation == 'piece':
                        weight = per_piece * lead.order_quantity
                    elif lead.order_presentation == 'dozen':
                        weight = per_piece * 12 * lead.order_quantity
                    elif lead.order_presentation == 'kilo':
                        weight = lead.order_quantity
            lead.order_total_weight = weight

    @api.depends('order_quantity', 'order_presentation', 'order_total_weight')
    def _compute_order_display(self):
        for lead in self:
            if lead.product_variant_id and lead.order_quantity > 0:
                if lead.order_presentation == 'kilo':
                    lead.order_display = f"{lead.order_quantity:.1f} kg"
                else:
                    pres_name = dict(self._fields['order_presentation'].selection).get(lead.order_presentation, '')
                    lead.order_display = f"{lead.order_quantity:.0f} {pres_name} ({lead.order_total_weight:.1f} kg)"
            else:
                lead.order_display = False

    @api.depends('product_variant_id', 'order_quantity', 'order_presentation', 'order_total_weight')
    def _compute_order_breakdown(self):
        for lead in self:
            if lead.order_presentation == 'kilo' and lead.order_quantity > 0 and lead.product_variant_id:
                variant = lead.product_variant_id
                try:
                    box_kg = float(variant.weight)
                except ValueError:
                    box_kg = 0.0
                pieces = variant.pieces_per_box or 360
                if pieces > 0 and box_kg > 0:
                    per_piece = box_kg / pieces
                    remaining = lead.order_quantity
                    cajas = int(remaining // box_kg)
                    remaining -= cajas * box_kg
                    peso_cono = per_piece * 30
                    conos = int(remaining // peso_cono)
                    remaining -= conos * peso_cono
                    peso_docena = per_piece * 12
                    docenas = int(remaining // peso_docena)
                    remaining -= docenas * peso_docena
                    piezas = round(remaining / per_piece)
                    total_calc = cajas * box_kg + conos * peso_cono + docenas * peso_docena + piezas * per_piece
                    result = []
                    if cajas: result.append(f"{cajas} Caja(s)")
                    if conos: result.append(f"{conos} Cono(s)")
                    if docenas: result.append(f"{docenas} Docena(s)")
                    if piezas: result.append(f"{piezas} Pieza(s)")
                    if not result:
                        result.append("Sin desglose")
                    lead.order_breakdown = f"{', '.join(result)} (Total: {total_calc:.2f} kg)"
                else:
                    lead.order_breakdown = False
            else:
                lead.order_breakdown = False

    @api.depends('order_presentation')
    def _compute_is_kilo(self):
        for lead in self:
            lead.is_kilo = lead.order_presentation == 'kilo'

    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        if self.scheduled_date and self.route_id:
            route = self.route_id
            schedules = route.schedule_ids
            if not schedules:
                return
            weekday = str(self.scheduled_date.weekday())
            day_schedules = schedules.filtered(lambda s: s.day_of_week == weekday)
            if not day_schedules:
                dias_disponibles = ', '.join(
                    dict(self.env['alze.route.schedule']._fields['day_of_week'].selection).get(d, '')
                    for d in schedules.mapped('day_of_week')
                )
                return {
                    'warning': {
                        'title': 'Día no disponible',
                        'message': (
                            f"La fecha {self.scheduled_date.strftime('%d/%m/%Y')} no está en los días de entrega de "
                            f"{route.name}.\n"
                            f"Días asignados: {dias_disponibles}\n"
                            f"Cambia la fecha."
                        ),
                    }
                }

    def _assign_driver_and_schedule(self):
        for lead in self:
            if lead.delivery_type == 'puerta':
                lead.assigned_driver_id = False
                continue
            if not lead.route_id or not lead.partner_id:
                lead.assigned_driver_id = False
                if not lead.scheduled_date:
                    lead.scheduled_date = False
                continue
            route = lead.route_id
            if not any(driver.assigned_partner_ids for driver in route.driver_ids):
                route._distribute_clients_auto()
            driver = self.env['alze.driver'].search([
                ('id', 'in', route.driver_ids.ids),
                ('assigned_partner_ids', 'in', lead.partner_id.id)
            ], limit=1)
            lead.assigned_driver_id = driver.id if driver else False
            if not lead.scheduled_date:
                next_dt = route._get_next_schedule_date()
                lead.scheduled_date = next_dt.date() if next_dt else False

    @api.onchange('partner_id', 'route_id')
    def _onchange_partner_or_route(self):
        if self.delivery_type != 'puerta':
            self._assign_driver_and_schedule()

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        for lead in leads:
            if lead.delivery_type != 'puerta':
                lead._assign_driver_and_schedule()
        return leads

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['partner_id', 'route_id', 'delivery_type']):
            for lead in self:
                if lead.delivery_type == 'puerta':
                    lead.assigned_driver_id = False
                else:
                    lead._assign_driver_and_schedule()
        return res

    def _utc_time_str(self, local_date, local_time_float):
        hours = int(local_time_float)
        minutes = int((local_time_float - hours) * 60)
        cst = pytz.timezone('America/Mexico_City')
        local_dt = cst.localize(datetime.combine(local_date, time(hours, minutes)))
        utc_dt = local_dt.astimezone(pytz.UTC)
        return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    def _get_start_point(self):
        self.ensure_one()
        if self.start_point_id:
            p = self.start_point_id
        else:
            p = self.env['alze.start.point'].search([], order='sequence, id', limit=1)
        if p:
            return {
                "singleUseLocation": {
                    "latitude": p.partner_latitude,
                    "longitude": p.partner_longitude,
                    "address": f"{p.street or ''}, {p.city or ''}",
                    "radiusMeters": p.radius_meters,
                },
                "notes": f"Punto de partida: {p.name}",
                "start_time": p.start_time,
            }
        return {
            "singleUseLocation": {
                "latitude": 19.090337487921406,
                "longitude": -98.18938446177314,
                "address": "Circuito, Interior Sur 13 A, Central de Abastos, 72019 Heroica Puebla de Zaragoza, Pue.",
                "radiusMeters": 250,
            },
            "notes": "Punto de partida (por defecto)",
            "start_time": 8.0,
        }

    def _build_stops_for_route(self, route):
        """Construye stops cumpliendo las reglas de Samsara: primera parada solo departure,
        última solo arrival, las intermedias ambos."""
        start = self._get_start_point()
        leads = route.lead_ids.filtered(
            lambda l: l.partner_id and l.partner_id.partner_latitude and l.partner_id.partner_longitude
        )
        stops = []
        a_lead = leads[0] if leads else self
        base_utc_str = self._utc_time_str(a_lead.scheduled_date, start["start_time"])
        # Punto de partida (solo salida)
        start_stop = {
            "singleUseLocation": start["singleUseLocation"],
            "notes": start["notes"],
            "scheduledDepartureTime": base_utc_str,
        }
        stops.append(start_stop)
        # Paradas de clientes
        for i, lead in enumerate(leads):
            partner = lead.partner_id
            stop = {
                "singleUseLocation": {
                    "latitude": partner.partner_latitude,
                    "longitude": partner.partner_longitude,
                    "address": partner.contact_address or "",
                    "radiusMeters": 250,
                },
                "notes": f"Pedido: {lead.order_display or lead.name}",
            }
            # Asignar tiempos según posición
            if len(leads) == 1:
                # Única parada: solo arrival
                stop["scheduledArrivalTime"] = self._utc_time_str(a_lead.scheduled_date, start["start_time"] + 2)
            elif i == 0:
                # Primera parada de cliente: arrival y departure
                stop["scheduledArrivalTime"] = self._utc_time_str(a_lead.scheduled_date, start["start_time"] + 2)
                stop["scheduledDepartureTime"] = self._utc_time_str(a_lead.scheduled_date, start["start_time"] + 2.5)
            elif i == len(leads) - 1:
                # Última parada: solo arrival
                stop["scheduledArrivalTime"] = self._utc_time_str(a_lead.scheduled_date, start["start_time"] + 2 + i)
            else:
                # Intermedia: ambos
                stop["scheduledArrivalTime"] = self._utc_time_str(a_lead.scheduled_date, start["start_time"] + 2 + i)
                stop["scheduledDepartureTime"] = self._utc_time_str(a_lead.scheduled_date, start["start_time"] + 2.5 + i)
            stops.append(stop)
        return stops

    def _optimize_route(self, route_id_samsara, token):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        optimize_url = f"https://api.samsara.com/fleet/routes/{route_id_samsara}/optimize"
        resp = requests.post(optimize_url, headers=headers)
        if resp.status_code not in (200, 204):
            _logger.warning("Error al optimizar ruta %s: %s", route_id_samsara, resp.text)

    def action_send_single_lead_to_samsara(self):
        self.ensure_one()
        lead = self
        if lead.delivery_type == 'puerta':
            raise UserError('Las entregas tipo Puerta no se envían a Samsara.')
        if not lead.product_variant_id:
            raise UserError('Este lead no tiene un producto asignado.')
        if not lead.partner_id:
            raise UserError('Este lead no tiene un cliente asignado.')
        if not lead.partner_id.partner_latitude or not lead.partner_id.partner_longitude:
            raise UserError('El cliente no tiene coordenadas de geolocalización.')
        if not lead.assigned_driver_id:
            raise UserError('Este lead no tiene un chofer asignado.')
        if not lead.scheduled_date:
            raise UserError('Este lead no tiene una fecha de entrega programada.')

        token = self.env['ir.config_parameter'].sudo().get_param('samsara_api_token')
        if not token:
            raise UserError('Token de Samsara no configurado.')

        driver = lead.assigned_driver_id
        if not driver.samsara_driver_id:
            driver.action_send_to_samsara()
            if not driver.samsara_driver_id:
                raise UserError('No se pudo obtener el ID Samsara del chofer. Intente enviarlo manualmente desde su ficha.')

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        arrival_date = lead.scheduled_date
        start = self._get_start_point()
        base_utc = self._utc_time_str(arrival_date, start["start_time"])

        route_name = f"{lead.route_id.name or driver.name} - {arrival_date.strftime('%Y-%m-%d')}"

        samsara_route = self.env['alze.samsara.route'].search([
            ('driver_id', '=', driver.id),
            ('date', '=', arrival_date),
            ('state', '=', 'active'),
        ], limit=1)

        if not samsara_route:
            # Crear nueva ruta con paradas mínimas
            start_stop = {
                "singleUseLocation": start["singleUseLocation"],
                "notes": start["notes"],
                "scheduledDepartureTime": base_utc,
            }
            lead_stop = {
                "singleUseLocation": {
                    "latitude": lead.partner_id.partner_latitude,
                    "longitude": lead.partner_id.partner_longitude,
                    "address": lead.partner_id.contact_address or "",
                    "radiusMeters": 250,
                },
                "notes": f"Pedido: {lead.order_display or lead.name}",
                "scheduledArrivalTime": self._utc_time_str(arrival_date, start["start_time"] + 1),
            }
            stops = [start_stop, lead_stop]
            body = {
                "name": route_name,
                "driverId": driver.samsara_driver_id,
                "stops": stops,
                "settings": {"optimize": "distance"}
            }
            create_url = "https://api.samsara.com/fleet/routes"
            create_resp = requests.post(create_url, headers=headers, json=body)
            if create_resp.status_code == 200:
                new_route_id = create_resp.json()["data"]["id"]
                # Optimizar inmediatamente después de crear
                self._optimize_route(new_route_id, token)
                samsara_route = self.env['alze.samsara.route'].create({
                    'name': route_name,
                    'samsara_route_id': new_route_id,
                    'driver_id': driver.id,
                    'date': arrival_date,
                })
                lead.write({
                    'samsara_route_id': samsara_route.id,
                    'samsara_stop_id': 'sent'
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Samsara',
                        'message': f'Ruta creada, lead enviado y optimizada (ID: {new_route_id})',
                        'type': 'success',
                    }
                }
            else:
                raise UserError('Error al crear ruta en Samsara: %s' % (create_resp.text or 'Respuesta vacía'))

        # Ruta existente: añadir lead y reconstruir stops
        lead.write({
            'samsara_route_id': samsara_route.id,
            'samsara_stop_id': 'sent'
        })
        stops = self._build_stops_for_route(samsara_route)

        update_url = f"https://api.samsara.com/fleet/routes/{samsara_route.samsara_route_id}"
        body = {"stops": stops}
        update_resp = requests.patch(update_url, headers=headers, json=body)
        if update_resp.status_code == 200:
            # Optimizar después de actualizar
            self._optimize_route(samsara_route.samsara_route_id, token)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Samsara',
                    'message': f'Lead añadido, ruta actualizada y optimizada.',
                    'type': 'success',
                }
            }
        else:
            raise UserError('Error al actualizar ruta en Samsara: %s' % update_resp.text)