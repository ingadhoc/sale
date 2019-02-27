##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import http, tools
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSalePortal(WebsiteSale):

    @http.route(['/portal_address'], type='http', methods=['GET', 'POST'],
                auth="public", website=True)
    def portal_address(self, **kw):
        Partner = request.env[
            'res.partner'].with_context(show_address=1).sudo()
        order = request.env['sale.order'].new({
            'partner_id': request.env.user.partner_id.commercial_partner_id.id
        })
        mode = (False, False)
        def_country_id = order.partner_id.country_id
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            mode = ('new', 'billing')
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search(
                    [('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                else:
                    shippings = Partner.search(
                        [('id', 'child_of',
                          order.partner_id.commercial_partner_id.ids)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                if mode:
                    values = Partner.browse(partner_id)
            elif partner_id == -1:
                mode = ('new', 'shipping')
            else:  # no mode - refresh without post?
                return request.redirect('/portal_addresses')

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(
                mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(
                order, mode, pre_values, errors, error_msg)

            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                partner_id = self._checkout_form_save(mode, post, kw)

                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.onchange_partner_id()
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id

                order.message_partner_ids = [
                    (4, partner_id),
                    (3, request.website.partner_id.id)]
                if not errors:
                    return request.redirect(
                        kw.get('callback') or '/portal_addresses')

        country = 'country_id' in values and values['country_id'] != '' \
            and request.env['res.country'].browse(int(values['country_id']))
        country = country and country.exists() or def_country_id
        render_values = {
            'website_sale_order': order,
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'country': country,
            'countries': country.get_website_sale_countries(mode=mode[1]),
            "states": country.get_website_sale_states(mode=mode[1]),
            'error': errors,
            'callback': kw.get('callback'),
        }
        # para evitar modulo puente con l10n_ar_website_sale lo hacemos asi
        if request.env['ir.module.module'].sudo().search([
                ('name', '=', 'l10n_ar_website_sale'),
                ('state', '=', 'installed')], limit=1):
            document_categories = request.env[
                'res.partner.id_category'].sudo().search([])
            afip_responsabilities = request.env[
                'afip.responsability.type'].sudo().search([])
            uid = request.session.uid or request.env.ref('base.public_user').id
            Partner = request.env['res.users'].browse(uid).partner_id
            Partner = Partner.with_context(show_address=1).sudo()
            render_values.update({
                'document_categories': document_categories,
                'afip_responsabilities': afip_responsabilities,
                'partner': Partner,
            })
        return request.render("portal_sale_distributor.portal_address",
                              render_values)

    @http.route(['/portal_addresses'],
                type='http', auth="public", website=True)
    def portal_addresses(self, **post):
        order = request.website.sale_get_order()
        order = request.env['sale.order'].new(
            {'partner_id':
             request.env.user.partner_id.commercial_partner_id.id})
        Partner = order.partner_id.with_context(show_address=1).sudo()
        shippings = Partner.search(
            [("id", "child_of", order.partner_id.commercial_partner_id.ids),
             '|', ("type", "in", ["delivery", "other"]),
             ("id", "=", order.partner_id.commercial_partner_id.id)],
            order='id desc')
        values = {'order': order, 'shippings': shippings}
        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render("portal_sale_distributor.addresses", values)
