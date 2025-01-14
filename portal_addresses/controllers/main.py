##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import json
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.tools import clean_context


class WebsiteSalePortal(WebsiteSale):
    @http.route(
        '/portal/address', type='http', methods=['GET'], auth='public', website=True, sitemap=False
    )
    def portal_address(
        self, partner_id=None, address_type='billing', use_delivery_as_billing=None, **query_params
    ):
        """ Display the address form.

        A partner and/or an address type can be given through the query string params to specify
        which address to update or create, and its type.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            delivery and the billing address. 'true' or 'false'.
        :param dict query_params: The additional query string parameters forwarded to
                                  `_prepare_address_form_values`.
        :return: The rendered address form.
        :rtype: str
        """
        partner_id = partner_id and int(partner_id)
        order_sudo = request.env['sale.order'].new({
            'partner_id': request.env.user.partner_id.commercial_partner_id.id
        })
        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id, address_type=address_type
        )

        if partner_sudo:  # If editing an existing partner.
            use_delivery_as_billing = (
                order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            )

        # Render the address form.
        address_form_values = self._prepare_address_form_values(
            order_sudo,
            partner_sudo,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            **query_params
        )
        return request.render('portal_addresses.portal_address', address_form_values)


    @http.route(['/portal/addresses'],
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
        billings = Partner.search([
            ("id", "child_of", order.partner_id.commercial_partner_id.ids),
            '|', ("type", "in", ["invoice", "other"]),
            ("id", "=", order.partner_id.commercial_partner_id.id)
        ], order='id desc')
        values = {
            'order': order,
            'website_sale_order': order,
            'delivery_addresses': shippings,
            'billing_addresses': billings
        }
        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render(
            "portal_addresses.addresses", values)

    @http.route(
        '/portal/address/submit', type='http', methods=['POST'], auth='public', website=True,
        sitemap=False
    )
    def portal_address_submit(
        self, partner_id=None, address_type='billing', use_delivery_as_billing=None, callback=None,
        required_fields=None, **form_data
    ):
        """ Create or update an address.

        If it succeeds, it returns the URL to redirect (client-side) to. If it fails (missing or
        invalid information), it highlights the problematic form input with the appropriate error
        message.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            billing and the delivery address. 'true' or 'false'.
        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param dict form_data: The form data to process as address values.
        :return: A JSON-encoded feedback, with either the success URL or an error message.
        :rtype: str
        """
        order_sudo = request.env['sale.order'].new({
            'partner_id': request.env.user.partner_id.commercial_partner_id.id
        })
        use_delivery_as_billing = False
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )
        # Parse form data into address values, and extract incompatible data as extra form data.
        address_values, extra_form_data = self._parse_form_data(form_data)

        is_main_address = order_sudo.partner_id.id == partner_sudo.id
        # Validate the address values and highlights the problems in the form, if any.
        invalid_fields, missing_fields, error_messages = self._validate_address_values(
            address_values,
            partner_sudo,
            address_type,
            use_delivery_as_billing,
            required_fields,
            is_main_address=is_main_address,
            **extra_form_data,
        )
        if error_messages:
            return json.dumps({
                'invalid_fields': list(invalid_fields | missing_fields),
                'messages': error_messages,
            })

        is_new_address = False
        if not partner_sudo:  # Creation of a new address.
            is_new_address = True
            self._complete_address_values(address_values, address_type, use_delivery_as_billing, order_sudo)
            clean_context(request.env.context)
            partner_sudo = (
                request.env["res.partner"]
                .sudo()
                .with_context(
                    **{
                        "tracking_disable": True,
                        "no_vat_validation": True,
                    }
                )
                .create(address_values)
            )
        elif not self._are_same_addresses(address_values, partner_sudo):
            partner_sudo.write(address_values)  # Keep the same partner if nothing changed.

        partner_fnames = set()
        if is_main_address:  # Main address updated.
            partner_fnames.add('partner_id')  # Force the re-computation of partner-based fields.

        if address_type == 'billing':
            partner_fnames.add('partner_invoice_id')
            if is_new_address and order_sudo.only_services:
                # The delivery address is required to make the order.
                partner_fnames.add('partner_shipping_id')
            callback = callback or self._get_extra_billing_info_route(order_sudo)
        elif address_type == 'delivery':
            partner_fnames.add('partner_shipping_id')
            if use_delivery_as_billing:
                partner_fnames.add('partner_invoice_id')

        if is_new_address or order_sudo.only_services:
            callback = callback or '/shop/checkout?try_skip_step=true'
        else:
            callback = callback or '/shop/checkout'

        self._handle_extra_form_data(extra_form_data, address_values)

        return json.dumps({
            'successUrl': callback,
        })
