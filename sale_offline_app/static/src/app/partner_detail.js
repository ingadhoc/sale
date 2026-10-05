import { Component } from "@odoo/owl";

export class PartnerDetail extends Component {
    static template = "sale_offline_app.PartnerDetail";
    static props = { partner: Object };

    get mapsUrl() {
        const { partner_latitude: lat, partner_longitude: lng } = this.props.partner;
        if (!lat && !lng) {
            return false;
        }
        return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
    }

    get rows() {
        const p = this.props.partner;
        return [
            ["Referencia", p.ref],
            ["CUIT / Documento", p.vat],
            ["Dirección", [p.street, p.street2].filter(Boolean).join(", ")],
            ["Ciudad", [p.zip, p.city].filter(Boolean).join(" ")],
            ["Provincia", p.state_id],
            ["País", p.country_id],
            ["Teléfono", p.phone],
            ["Email", p.email],
            ["Lista de precios", p.property_product_pricelist],
            ["Posición fiscal", p.fiscal_position_name],
        ].filter(([, value]) => value);
    }
}
