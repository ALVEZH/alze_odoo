from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrJob(models.Model):
    _inherit = 'hr.job'

    x_salary_min = fields.Monetary(
        string='Salario Mínimo',
        currency_field='currency_id',
        help='Rango salarial mínimo para este puesto'
    )
    x_salary_max = fields.Monetary(
        string='Salario Máximo',
        currency_field='currency_id',
        help='Rango salarial máximo para este puesto'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    @api.constrains('x_salary_min', 'x_salary_max')
    def _check_ranges(self):
        for record in self:
            if record.x_salary_min and record.x_salary_max:
                if record.x_salary_min > record.x_salary_max:
                    raise ValidationError("El salario mínimo no puede ser mayor al salario máximo.")