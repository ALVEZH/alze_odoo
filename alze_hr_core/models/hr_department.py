from odoo import models, fields

class HrDepartment(models.Model):
    _inherit = 'hr.department'
    sede_principal_id = fields.Many2one('alze.sede', string='Sede')