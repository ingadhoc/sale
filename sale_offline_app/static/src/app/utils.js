/** Date of today (plus some days) in the device timezone, as YYYY-MM-DD. */
export function localDate(offsetDays = 0) {
    const now = new Date();
    now.setDate(now.getDate() + offsetDays);
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export function formatDate(iso) {
    return iso ? new Date(iso).toLocaleString("es-AR", { hourCycle: "h23" }) : "";
}

export function partnerTitle(partner) {
    return partner.ref ? `${partner.ref} - ${partner.name}` : partner.name;
}

export function mapsUrl(query) {
    return query && `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}
