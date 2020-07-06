import hashlib
import json
from odoo import models
from odoo.http import request
from odoo.tools import ustr

from odoo.addons.web.controllers.main import module_boot, HomeStaticTemplateHelpers


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):

        user = request.env.user

        user_context = request.session.get_context() if request.session.uid else {}

        result = super().session_info()
        if self.env.user.has_group('base.group_portal'):
            # the following is only useful in the context of a webclient bootstrapping
            # but is still included in some other calls (e.g. '/web/session/authenticate')
            # to avoid access errors and unnecessary information, it is only included for users
            # with access to the backend ('internal'-type users)
            mods = module_boot()
            qweb_checksum = HomeStaticTemplateHelpers.get_qweb_templates_checksum(
                addons=mods, debug=request.session.debug)
            lang = user_context.get("lang")
            translation_hash = request.env['ir.translation'].get_web_translations_hash(
                mods, lang)
            menu_json_utf8 = json.dumps(request.env['ir.ui.menu'].load_menus(
                request.session.debug), default=ustr, sort_keys=True).encode()
            cache_hashes = {
                "load_menus": hashlib.sha1(menu_json_utf8).hexdigest(),
                "qweb": qweb_checksum,
                "translations": translation_hash,
            }
            result.update({
                # current_company should be default_company
                "user_companies": {
                    'current_company': (user.company_id.id, user.company_id.name),
                    'allowed_companies': [(comp.id, comp.name) for comp in user.company_ids]},
                "currencies": self.get_currencies(),
                "show_effect": True,
                "display_switch_company_menu": user.has_group(
                    'base.group_multi_company') and len(user.company_ids) > 1,
                "cache_hashes": cache_hashes,
            })
        return result
