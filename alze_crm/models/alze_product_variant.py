from odoo import models, fields, api

class AlzeProductVariant(models.Model):
    _name = 'alze.product.variant'
    _description = 'Variante de Producto'
    _rec_name = 'code'
    _order = 'template_id, prefix, weight, suffix'

    template_id = fields.Many2one('alze.product.template', string='Producto', required=True, ondelete='cascade')
    prefix = fields.Selection([('HB', 'HB'), ('HR', 'HR')], string='Prefijo', required=True, default='HB')
    weight = fields.Char(string='Peso', required=True, default='22')
    suffix = fields.Selection([('A', 'A'), ('B', 'B')], string='Sufijo', required=True, default='A')
    quality = fields.Selection([
        ('first', 'Primera Calidad'),
        ('second', 'Segunda Calidad'),
    ], string='Calidad', required=True, default='first')
    active = fields.Boolean(string='Disponible', default=True)
    code = fields.Char(string='Código', compute='_compute_code', store=True)
    zone_id = fields.Many2one('res.company', string='Zona', default=lambda self: self.env.company)

    # Configuración de piezas
    pieces_per_box = fields.Integer(string='Piezas por Caja', default=360, required=True)
    box_weight_float = fields.Float(string='Peso Caja (kg)', compute='_compute_weights', digits=(12, 2))

    # Campos de visualización (Los que el usuario verá)
    weight_per_piece_display = fields.Char(string='Peso por Pieza', compute='_compute_weight_displays')
    weight_12_pack_display = fields.Char(string='Peso Docenero', compute='_compute_weight_displays')
    weight_cono_display = fields.Char(string='Peso Cono (30 pzas)', compute='_compute_weight_displays')

    @api.depends('prefix', 'weight', 'suffix')
    def _compute_code(self):
        for variant in self:
            variant.code = f"{variant.prefix}{variant.weight}{variant.suffix}"

    @api.depends('weight', 'pieces_per_box')
    def _compute_weights(self):
        for variant in self:
            try:
                variant.box_weight_float = float(variant.weight)
            except ValueError:
                variant.box_weight_float = 0.0

    @api.depends('box_weight_float', 'pieces_per_box')
    def _compute_weight_displays(self):
        for variant in self:
            pieces = variant.pieces_per_box
            box_kg = variant.box_weight_float
            
            if pieces > 0:
                per_piece = box_kg / pieces
                p_12 = per_piece * 12
                p_30 = per_piece * 30
                
                # Cálculo de cuántos caben en la caja
                fits_12 = pieces / 12
                fits_30 = pieces / 30

                variant.weight_per_piece_display = f"{per_piece:.4f} kg ({int(round(per_piece*1000))} g)"
                variant.weight_12_pack_display = f"{p_12:.4f} kg ({int(round(p_12*1000))} g) {fits_12:.1f} en caja"
                variant.weight_cono_display = f"{p_30:.4f} kg ({int(round(p_30*1000))} g) {fits_30:.1f} en caja"
            else:
                variant.weight_per_piece_display = "0.0000 kg"
                variant.weight_12_pack_display = "0.0000 kg"
                variant.weight_cono_display = "0.0000 kg"