##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    qty = fields.Float(
        'Quantity',
        compute='_compute_qty',
        inverse='_inverse_qty',
    )

    @api.multi
    def write(self, vals):
        """
        If in vals only comes qty and force_product_edit then it is a dummy
        write and we do it with sudo
        """
        if len(vals) == 1 and vals.get('qty', False) and self._context.get(
                'force_product_edit', False):
            return super(ProductProduct, self.sudo()).write(vals)
        return super(ProductProduct, self).write(vals)

    @api.multi
    def _compute_qty(self):
        sale_order_id = self._context.get('active_id', False)
        if not sale_order_id:
            self.update({'qty': 0.0})
            return

        sale_order_lines = self.env['sale.order'].browse(
            sale_order_id).order_line
        for rec in self:
            lines = sale_order_lines.filtered(
                lambda so: so.product_id == rec)
            qty = sum([line.product_uom._compute_quantity(
                line.product_uom_qty,
                rec.uom_id) for line in lines])
            rec.update({'qty': qty})

    @api.multi
    def _inverse_qty(self):
        sale_order_id = self._context.get('active_id', False)
        if not sale_order_id:
            return
        sale_order = self.env['sale.order'].browse(sale_order_id)
        sale_order_lines = sale_order.order_line
        for rec in self:
            qty = rec.qty
            lines = sale_order_lines.filtered(
                lambda so: so.product_id == rec)
            if lines:
                (lines - lines[0]).unlink()
                lines[0].update({
                    'product_uom_qty': qty,
                    'product_uom': rec.uom_id.id,
                })
            else:
                sale_order.add_products(rec.id, qty)

    @api.multi
    def action_product_form(self):
        self.ensure_one()
        return self.get_formview_action()

    @api.multi
    def action_product_add_one(self):
        for rec in self:
            rec.update({
                'qty': rec.qty + 1})
