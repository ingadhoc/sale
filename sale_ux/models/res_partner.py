from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model_create_multi
    def create(self, vals_list):
        # Evitamos que Odoo setee automáticamente el campo company-dependent
        # `specific_property_product_pricelist` al crear un partner, salvo que el usuario
        # lo haya definido explícitamente en valores por defecto. De esta forma, las compañías sin valor seteado
        # utilizarán el fallback por orden de secuencia, permitiendo que los cambios
        # de prioridad en las listas de precios se reflejen dinámicamente

        partners = super().create(vals_list)
        # Buscamos primera lista en secuencia porque los default no los tenemos cargados aun. Por eso usamos este hack
        pricelist = self.env["product.pricelist"].search([], limit=1, order="sequence")
        for partner, vals in zip(partners, vals_list):
            if "specific_property_product_pricelist" not in vals:
                default_pricelist_id = vals.get("property_product_pricelist")

                if not default_pricelist_id:
                    default_pricelist_id = (
                        self.env["ir.default"]
                        ._get_model_defaults(self._name)
                        .get("specific_property_product_pricelist", False)
                    )

                if default_pricelist_id:
                    if default_pricelist_id != pricelist.id:
                        partner.specific_property_product_pricelist = default_pricelist_id
                    else:
                        partner.specific_property_product_pricelist = None
                else:
                    partner.specific_property_product_pricelist = None

        return partners
