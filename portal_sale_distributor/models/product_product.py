##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
import json
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'tree':
            if self.env.user.has_group('portal_sale_distributor.group_portal_backend_distributor'):
                # ocultamos campos de módulos de los cuales no depende
                fields = (arch.xpath("//field[@name='taxed_lst_price']")
                        + arch.xpath("//field[@name='website_id']")
                        + arch.xpath("//field[@name='is_published']"))
                for node in fields:
                    node.set('invisible', '1')
                    modifiers = json.loads(node.get("modifiers") or "{}")
                    modifiers['invisible'] = True
                    node.set("modifiers", json.dumps(modifiers))
        return arch, view

    def _portal_archive_unarchive(self):
        if self.env.user.has_group('portal_sale_distributor.group_portal_backend_distributor'):
            raise ValidationError(_('Portal users may not archive or unarchive records.'))

    def action_archive(self):
        self._portal_archive_unarchive()
        return super().action_archive()

    def action_unarchive(self):
        self._portal_archive_unarchive()
        return super().action_unarchive()
