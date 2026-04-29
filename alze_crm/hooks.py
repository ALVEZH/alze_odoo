from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def _post_init_hook(env):
    """Oculta el menú original de Clientes del CRM si existe."""
    try:
        # Intentar con el ID estándar de Odoo 17
        menu = env.ref('crm.crm_menu_customer', raise_if_not_found=False)
        if menu:
            menu.write({'active': False})
            _logger.info("Menú 'Clientes' original del CRM ocultado correctamente.")
        else:
            # Búsqueda alternativa por nombre y padre
            crm_root = env.ref('crm.crm_menu_root', raise_if_not_found=False)
            if crm_root:
                original_menu = env['ir.ui.menu'].search([
                    ('name', '=', 'Clientes'),
                    ('parent_id', '=', crm_root.id)
                ], limit=1)
                if original_menu:
                    original_menu.write({'active': False})
                    _logger.info("Menú 'Clientes' (alternativo) ocultado.")
                else:
                    _logger.warning("No se encontró ningún menú 'Clientes' en CRM para ocultar.")
    except Exception as e:
        _logger.error("Error en _post_init_hook: %s", e)