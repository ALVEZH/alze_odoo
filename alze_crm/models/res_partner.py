from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_crm_customer = fields.Boolean(
        string="Es Cliente de CRM",
        default=False,
        copy=False
    )