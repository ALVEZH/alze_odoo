from odoo import models, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_open_driver(self):
        self.ensure_one()
        driver = self.env['alze.driver'].search([('employee_id', '=', self.id)], limit=1)
        if not driver:
            driver = self.env['alze.driver'].create({'employee_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'alze.driver',
            'res_id': driver.id,
            'view_mode': 'form',
            'target': 'current',
        }