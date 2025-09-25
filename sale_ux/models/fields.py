# my_module/models/fields_patch.py
from odoo import fields, SUPERUSER_ID

_original_get_company_dependent_fallback = fields.Field.get_company_dependent_fallback

def _patched_get_company_dependent_fallback(self, records):
    # modificás el contexto antes de llamar al original
    ctx = dict(records.env.context)
    if records._name == "res.partner" and records.ids and len(records) == 1:
        params = ctx.get("params", {})
        params = dict(params)
        params["resId"] = records.id
        ctx["params"] = params

    # llamás al método original con el nuevo contexto
    return _original_get_company_dependent_fallback(self, records.with_context(ctx))

# patch global: reemplaza el método en TODAS las instancias de Field
fields.Field.get_company_dependent_fallback = _patched_get_company_dependent_fallback
