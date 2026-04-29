from odoo import models, fields

class AlzeProductTemplate(models.Model):
    _name = 'alze.product.template'
    _description = 'Plantilla de Producto'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción')
    variant_ids = fields.One2many('alze.product.variant', 'template_id', string='Variantes')
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)