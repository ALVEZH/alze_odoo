from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sede_id = fields.Many2one('alze.sede', string='Sede Actual')
    sede_full_address = fields.Char(related='sede_id.full_address', readonly=True)