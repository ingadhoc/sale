from odoo import SUPERUSER_ID, api
from odoo.addons.pos_ux.hooks import post_init_hook


def migrate(cr, version):
    """Databases where pos_ux was already installed never ran the install hook."""
    post_init_hook(api.Environment(cr, SUPERUSER_ID, {}))
