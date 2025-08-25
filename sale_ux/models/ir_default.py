import json

from odoo import models


class IrDefault(models.Model):
    _inherit = "ir.default"

    def _get_model_defaults(self, model_name, condition=False):
        res = super()._get_model_defaults(model_name, condition)
        if model_name == "res.partner":
            specific_property_pricelist = self.get_default_pricelist()
            if specific_property_pricelist:
                res["specific_property_product_pricelist"] = specific_property_pricelist
        return res

    def get_default_pricelist(self):
        # Si es publico/portal evitamos el método
        if self.env.user._is_public():
            return
        field = self.env["ir.model.fields"]._get("res.partner", "specific_property_product_pricelist")
        default = (
            self.env["ir.default"]
            .sudo()
            .search(
                [
                    ("field_id", "=", field.id),
                    ("user_id", "=", self.env.context.get("uid", self.env.user.id)),
                    ("json_value", "!=", False),
                    ("company_id", "in", [self.env.company.id, False]),
                ],
                limit=1,
                order="company_id desc",
            )
        )
        return json.loads(default.json_value) if default else None
