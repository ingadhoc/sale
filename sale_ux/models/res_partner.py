from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    specific_property_product_pricelist = fields.Many2one(
        string="Assigned Pricelist",
        help=(
            "Manually set a specific pricelist for this partner. If left blank, the system will "
            "automatically determine the best match based on priority rules."
        ),
    )
    property_product_pricelist = fields.Many2one(
        string="Effective Pricelist",
        help=(
            "The pricelist that will actually be applied to sales. It reflects the assigned list "
            "above or, if none, the one calculated by Odoo's sequence and applicability rules."
        ),
    )

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
                # Los subcontactos heredan la lista de precios del contacto comercial
                # (empresa matriz) a través del mecanismo de commercial_fields de Odoo.
                # No debemos pisar ese valor o el subcontacto perderá la herencia.
                if partner.parent_id:
                    continue
                default_pricelist_id = vals.get("property_product_pricelist")

                if not default_pricelist_id:
                    default_pricelist_id = (
                        self.env["ir.default"]._get_model_defaults(self._name).get("property_product_pricelist", False)
                    )

                if default_pricelist_id:
                    if default_pricelist_id != pricelist.id:
                        partner.specific_property_product_pricelist = default_pricelist_id
                    else:
                        partner.specific_property_product_pricelist = None
                else:
                    partner.specific_property_product_pricelist = None

        return partners

    @api.model
    def get_import_templates(self):
        if self.env.context.get("res_partner_search_mode") == "customer":
            return [
                {
                    "label": _("Import Template for Customers"),
                    "template": "/sale_ux/static/xls/res_partner.xlsx",
                }
            ]
        return super().get_import_templates()
