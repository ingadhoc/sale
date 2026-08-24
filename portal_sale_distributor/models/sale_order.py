##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import json

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    activity_date_deadline = fields.Date(
        groups="base.group_user,portal_sale_distributor.group_portal_backend_distributor"
    )
    message_partner_ids = fields.Many2many(
        groups="base.group_user,portal_sale_distributor.group_portal_backend_distributor"
    )
    tag_ids = fields.Many2many(
        groups="sales_team.group_sale_salesman,portal_sale_distributor.group_portal_backend_distributor"
    )

    def action_confirm_distributor(self):
        if self.detect_exceptions() != []:
            self.sudo().message_post(
                body=_(
                    "El pedido no puede ser confirmado por %s porque contiene excepciones, debe ser revisado por un administrador"
                )
                % self.env.user.name,
                subtype_id=self.env.ref("mail.mt_comment").id,
            )
        else:
            self.sudo().message_post(
                body=_("Pedido confirmado por %s") % self.env.user.name, subtype_id=self.env.ref("mail.mt_comment").id
            )
            self = self.sudo()
            return self.action_confirm()

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == "form" and self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"):
            # restringimos acceso
            fields = (
                arch.xpath("//field[@name='partner_id']")
                + arch.xpath("//field[@name='partner_invoice_id']")
                + arch.xpath("//field[@name='partner_shipping_id']")
            )
            for node in fields:
                node.set("options", "{'no_create': True, 'no_open': True}")

            # cambiamos atributos solo para portal
            readonly_fields = (
                arch.xpath("//field[@name='price_unit']")
                + arch.xpath("//field[@name='discount']")
                + arch.xpath("//field[@name='discount1']")
                + arch.xpath("//field[@name='discount2']")
                + arch.xpath("//field[@name='discount3']")
                + arch.xpath("//field[@name='tax_ids']")
                + arch.xpath("//field[@name='validity_days']")
                + arch.xpath("//field[@name='validity_date']")
            )
            for node in readonly_fields:
                node.set("readonly", "1")
                node.set("force_save", "1")
                modifiers = json.loads(node.get("modifiers") or "{}")
                modifiers["readonly"] = True
                modifiers["force_save"] = True
                node.set("modifiers", json.dumps(modifiers))

            # ocultamos header original, pestaña otra información y pestaña Quote Builder
            page = (
                arch.xpath("//button[@id='create_invoice']/..")
                + arch.xpath("//page[@name='other_information']")
                + arch.xpath("//page[@name='pdf_quote_builder']")
            )
            for node in page:
                node.set("invisible", "1")
                node.set("force_save", "1")
                modifiers = json.loads(node.get("modifiers") or "{}")
                modifiers["invisible"] = True
                modifiers["force_save"] = True
                node.set("modifiers", json.dumps(modifiers))

            # ocultamos campos de módulos de los cuales no depende
            invisible_fields = (
                arch.xpath("//field[@name='ignore_exception']")
                + arch.xpath("//label[@for='recurrence_id']")
                + arch.xpath("//field[@name='recurrence_id']")
                # its invisible modifier reads project_ids, and computing that field searches
                # projects by reinvoiced_sale_order_id, restricted to salesmen. Hiding the button
                # drops the modifier, so the field is no longer added to the view nor read.
                + arch.xpath("//button[@name='action_view_milestone']")
                # sale.order.margin carries no groups, unlike its line level counterparts. The
                # whole block, or the label and the percentage are left behind.
                + arch.xpath("//label[@for='margin']/..")
            )
            for node in invisible_fields:
                node.set("invisible", "1")
                node.set("force_save", "1")
                modifiers = json.loads(node.get("modifiers") or "{}")
                modifiers["invisible"] = True
                modifiers["force_save"] = True
                node.set("modifiers", json.dumps(modifiers))
        return arch, view

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type="form", **options):
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.user.has_group("portal_sale_distributor.group_portal_backend_distributor"),)

    def action_update_prices(self):
        self = self.sudo()
        super().action_update_prices()

    def _message_get_suggested_recipients_batch(self, **kwargs):
        # to keep odoobot out of the suggestions, mail reads base.partner_root.email_normalized
        # without sudo, and a portal user can not read that contact: the chatter fails to load
        # right after the distributor confirms the order. They do not add recipients anyway.
        if not self.env.user.has_group("base.group_user"):
            return {record.id: [] for record in self}
        return super()._message_get_suggested_recipients_batch(**kwargs)
