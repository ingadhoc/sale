##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    activity_date_deadline = fields.Date(
        groups="base.group_user,"
        "portal_sale_distributor.group_portal_backend_distributor"
    )

    def action_confirm_distributor(self):
        if self.detect_exceptions() != []:
            self.sudo().message_post(
            body=_("El pedido no puede ser confirmado por %s porque contiene excepciones, debe ser revisado por un administrador") % self.env.user.name,
            subtype_id=self.env.ref('mail.mt_comment').id)
        else:
            self.sudo().message_post(
                body=_("Pedido confirmado por %s") % self.env.user.name,
                subtype_id=self.env.ref('mail.mt_comment').id)
            self = self.sudo()
            return self.action_confirm()

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        """ desactivamos warning para portal distributor
        """
        if self.env.user.has_group(
                'portal_sale_distributor.group_portal_backend_distributor'):
            return {}
        else:
            return super()._onchange_partner_id_warning()

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form' and self.env.user.has_group('portal_sale_distributor.group_portal_backend_distributor'):
            # restringimos acceso
            fields = (arch.xpath("//field[@name='partner_id']")
                    + arch.xpath("//field[@name='partner_invoice_id']")
                    + arch.xpath("//field[@name='partner_shipping_id']"))
            for node in fields:
                node.set('options', "{'no_create': True, 'no_open': True}")

            # cambiamos atributos solo para portal
            readonly_fields = (arch.xpath("//field[@name='price_unit']")
                    + arch.xpath("//field[@name='discount']")
                    + arch.xpath("//field[@name='discount1']")
                    + arch.xpath("//field[@name='discount2']")
                    + arch.xpath("//field[@name='discount3']")
                    + arch.xpath("//field[@name='tax_id']")
                    + arch.xpath("//field[@name='validity_days']")
                    )
            for node in readonly_fields:
                node.set('readonly', '1')
                node.set('force_save', '1')
                modifiers = json.loads(node.get("modifiers") or "{}")
                modifiers['readonly'] = True
                modifiers['force_save'] = True
                node.set("modifiers", json.dumps(modifiers))

            # ocultamos header original, pestaña otra información y pestaña Quote Builder
            page = (arch.xpath("//button[@id='create_invoice']/..")
                    + arch.xpath("//page[@name='other_information']")
                    + arch.xpath("//page[@name='pdf_quote_builder']"))
            for node in page:
                node.set('invisible', '1')
                node.set('force_save', '1')
                modifiers = json.loads(node.get("modifiers") or "{}")
                modifiers['invisible'] = True
                modifiers['force_save'] = True
                node.set("modifiers", json.dumps(modifiers))

            # ocultamos campos de módulos de los cuales no depende
            invisible_fields = (arch.xpath("//field[@name='ignore_exception']")
                    + arch.xpath("//label[@for='recurrence_id']")
                    + arch.xpath("//field[@name='recurrence_id']")
                    + arch.xpath("//button[@name='update_date_prices_and_validity']")
                    )
            for node in invisible_fields:
                node.set('invisible', '1')
                node.set('force_save', '1')
                modifiers = json.loads(node.get("modifiers") or "{}")
                modifiers['invisible'] = True
                modifiers['force_save'] = True
                node.set("modifiers", json.dumps(modifiers))
        return arch, view

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.user.has_group('portal_sale_distributor.group_portal_backend_distributor'),)

    def action_update_prices(self):
        self = self.sudo()
        super().action_update_prices()
