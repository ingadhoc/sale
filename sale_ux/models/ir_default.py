import json

from odoo import models


class IrDefault(models.Model):
    _inherit = "ir.default"

    def _get_model_defaults(self, model_name, condition=False):
        res = super()._get_model_defaults(model_name, condition)
        if model_name == "res.partner":
            partner = None
            params = self.env.context.get("params")
            if params and params.get("resId"):
                partner = self.env["res.partner"].browse(params["resId"])
                if not partner.exists():
                    partner = None
            specific_property_pricelist = self.get_default_pricelist(partner)
            if specific_property_pricelist:
                res["specific_property_product_pricelist"] = specific_property_pricelist
        return res

    def get_default_pricelist(self, partner=None):
        # Si es publico/portal evitamos el método
        if self.env.user._is_public():
            return
        field = self.env["ir.model.fields"]._get("res.partner", "specific_property_product_pricelist")
        # Si se pasa un registro de partner, usar su usuario creador
        user_id = self.env.context.get("uid", self.env.user.id)
        if partner and hasattr(partner, "create_uid") and partner.create_uid:
            user_id = partner.create_uid.id
        default = (
            self.env["ir.default"]
            .sudo()
            .search(
                [
                    ("field_id", "=", field.id),
                    ("user_id", "in", [user_id, False]),
                    ("json_value", "!=", False),
                    ("company_id", "in", [self.env.company.id, False]),
                ],
                limit=1,
                order="user_id asc, company_id desc",
            )
        )
        return json.loads(default.json_value) if default else None
