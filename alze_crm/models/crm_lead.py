from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    route_id = fields.Many2one('alze.route', string='Ruta Asignada')

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        for lead in leads:
            if lead.partner_id:
                lead.partner_id.write({'is_crm_customer': True})
        return leads

    def write(self, vals):
        res = super().write(vals)
        if 'partner_id' in vals:
            for lead in self:
                if lead.partner_id:
                    lead.partner_id.write({'is_crm_customer': True})
        return res