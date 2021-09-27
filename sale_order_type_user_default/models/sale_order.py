from odoo import api, models


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.model
    def _default_type_id(self):
        return self.env.user.default_sale_order_type_id or super()._default_type_id()

    def _compute_sale_type_id(self):
        sales = self.env['sale.order']
        user_type = self.env.user.default_sale_order_type_id
        if user_type:
            for rec in self:
                # use default user type if:
                # 1. type dont have company or is same as sale order
                # 2. there is no default type on partner or commercial partner
                if (not user_type.company_id or user_type.company_id == rec.company_id) and not \
                        rec.partner_id.with_context(force_company=rec.company_id.id).sale_type and not \
                        rec.partner_id.commercial_partner_id.with_context(force_company=rec.company_id.id).sale_type:
                    sales += rec
                    rec.type_id = self.env.user.default_sale_order_type_id
        super(SaleOrder, self - sales)._compute_sale_type_id()
