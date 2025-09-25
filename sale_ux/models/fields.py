from odoo import fields

_original_get_company_dependent_fallback = fields.Field.get_company_dependent_fallback


def _patched_get_company_dependent_fallback(self, records):
    ctx = dict(records.env.context)
    if records._name == "res.partner" and records.ids and len(records) == 1:
        params = ctx.get("params", {})
        params = dict(params)
        params["resId"] = records.id
        ctx["params"] = params

    return _original_get_company_dependent_fallback(self, records.with_context(**ctx))


fields.Field.get_company_dependent_fallback = _patched_get_company_dependent_fallback
