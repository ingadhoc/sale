##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import http
from odoo.http import request
from werkzeug.exceptions import Forbidden
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSalePortal(WebsiteSale):


    @http.route(['/portal/address'], type='http', methods=['GET', 'POST'],
                auth="public", website=True)
    def portal_address(self, **kw):
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.env['sale.order'].new({
            'partner_id': request.env.user.partner_id.commercial_partner_id.id
        })
        
        mode = (False, False)
        values, errors = {}, {}
        partner_id = int(kw.get('partner_id', -1))

        if partner_id > 0:
            partner_type = request.env['res.partner'].browse(partner_id).type
            values = Partner.browse(partner_id)
            if partner_type == 'invoice':
                mode = ('edit', 'billing')
            else:
                mode = ('edit', 'shipping')
        elif partner_id == -1:
            mode = ('new', kw.get('mode') or 'shipping')
        else:  # no mode - refresh without post?
            return request.redirect('/portal/addresses')

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(kw)
            errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)
            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                partner_id = self._portal_address_form_save(mode, post, kw)
                if isinstance(partner_id, Forbidden):
                    return partner_id
            if mode[1] == 'billing':
                order.partner_id = partner_id
            elif mode[1] == 'shipping':
                order.partner_shipping_id = partner_id

            order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]
            if not errors:
                return request.redirect(kw.get('callback') or '/portal/addresses')

        render_values = {
            'website_sale_order': order,
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'error': errors,
            'callback': kw.get('callback'),
            'only_services': order and order.only_services,
            'account_on_checkout': request.website.account_on_checkout,
            'is_public_user': request.website.is_public_user()
        }
        # para evitar modulo puente con l10n_ar_website_sale lo hacemos asi
        if request.env['ir.module.module'].sudo().search([
                ('name', '=', 'l10n_ar_website_sale'),
                ('state', '=', 'installed')], limit=1):
            document_categories = request.env[
                'l10n_latam.document.type'].sudo().search([])
            afip_responsabilities = request.env[
                'l10n_ar.afip.responsibility.type'].sudo().search([])
            uid = request.session.uid or request.env.ref('base.public_user').id
            Partner = request.env['res.users'].browse(uid).partner_id
            Partner = Partner.with_context(show_address=1).sudo()
            render_values.update({
                'document_categories': document_categories,
                'afip_responsabilities': afip_responsabilities,
                'partner': Partner,
            })
        render_values.update(self._get_country_related_render_values(kw, render_values))
        return request.render("portal_addresses.portal_address", render_values)

    def _portal_address_form_save(self, mode, checkout, all_values):
        Partner = request.env['res.partner']
        if mode[0] == 'new':
            partner_id = Partner.sudo().create(checkout).id
        elif mode[0] == 'edit':
            partner_id = int(all_values.get('partner_id', 0))
            if partner_id:
                # double check
                partner = request.env.user.partner_id
                shippings = Partner.sudo().search(
                    [("id", "child_of", partner.commercial_partner_id.ids)])
                if partner_id not in shippings.mapped('id') and \
                        partner_id != partner.id:
                    return Forbidden()
                Partner.browse(partner_id).sudo().write(checkout)
        return partner_id

    @http.route(['/portal/addresses'],
                type='http', auth="public", website=True)
    def portal_addresses(self, **post):
        order = request.website.sale_get_order()
        order = request.env['sale.order'].new(
            {'partner_id':
             request.env.user.partner_id.commercial_partner_id.id})
        order.pricelist_id = order.partner_id.property_product_pricelist \
            and order.partner_id.property_product_pricelist.id or False
        Partner = order.partner_id.with_context(show_address=1).sudo()
        shippings = Partner.search(
            [("id", "child_of", order.partner_id.commercial_partner_id.ids),
             '|', ("type", "in", ["delivery", "other"]),
             ("id", "=", order.partner_id.commercial_partner_id.id)],
            order='id desc')
        billings = Partner.search([
            ("id", "child_of", order.partner_id.commercial_partner_id.ids),
            '|', ("type", "in", ["invoice", "other"]),
            ("id", "=", order.partner_id.commercial_partner_id.id)
        ], order='id desc')
        values = {
            'order': order,
            'website_sale_order': order,
            'shippings': shippings,
            'billings': billings
        }
        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render(
            "portal_addresses.addresses", values)
