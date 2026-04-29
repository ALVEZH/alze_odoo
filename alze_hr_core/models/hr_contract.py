from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    salary_out_of_range = fields.Boolean(compute='_compute_salary_out_of_range', store=True)
    x_force_save = fields.Boolean(string="Forzar Guardado", default=False, copy=False)
    
    # Campos relacionados para leer los rangos desde el puesto
    x_salary_min = fields.Monetary(related='job_id.x_salary_min', string='Salario Mínimo', readonly=True)
    x_salary_max = fields.Monetary(related='job_id.x_salary_max', string='Salario Máximo', readonly=True)
    currency_id = fields.Many2one(related='job_id.currency_id', readonly=True)

    @api.depends('wage', 'job_id.x_salary_min', 'job_id.x_salary_max')
    def _compute_salary_out_of_range(self):
        for contract in self:
            out = False
            if contract.job_id:
                min_s = contract.job_id.x_salary_min or 0.0
                max_s = contract.job_id.x_salary_max or 0.0
                wage = contract.wage or 0.0
                if (min_s > 0 or max_s > 0) and (wage < min_s or wage > max_s):
                    out = True
            contract.salary_out_of_range = out

    @api.onchange('wage')
    def _onchange_wage_reset_confirmation(self):
        if self.x_force_save:
            self.x_force_save = False

    # Lógica de Sedes
    contract_sede_id = fields.Many2one('alze.sede', string='Sede (contrato)')
    contract_sede_full_address = fields.Char(related='contract_sede_id.full_address', readonly=True)