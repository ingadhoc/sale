##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.osv.orm import setup_modifiers
from lxml import etree


class ProductProduct(models.Model):
    _inherit = "product.product"

    qty = fields.Float(
        'Quantity',
        compute='_compute_qty',
        inverse='_inverse_qty',
    )

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        """
        If we came from sale order, we send in context 'force_product_edit'
        and we change tree view to make editable and also field qty
        """
        res = super(ProductProduct, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        sale_quotation_products = self._context.get('sale_quotation_products')
        if sale_quotation_products and view_type == 'tree':
            doc = etree.XML(res['arch'])

            # make all fields not editable
            for node in doc.xpath("//field"):
                node.set('readonly', '1')
                setup_modifiers(node, res['fields'], in_tree_view=True)

            # add qty field
            placeholder = doc.xpath("//field[1]")[0]
            placeholder.addprevious(
                etree.Element('field', {
                    'name': 'qty',
                    # we force editable no matter user rights
                    'readonly': '0',
                }))
            # add button add one
            placeholder.addprevious(
                etree.Element('button', {
                    'name': 'action_product_add_one',
                    'type': 'object',
                    'icon': 'fa-plus',
                    'string': _('Add one'),
                }))
            res['fields'].update(self.fields_get(['qty']))

            # add button tu open form
            placeholder = doc.xpath("//tree")[0]
            placeholder.append(
                etree.Element('button', {
                    'name': 'action_product_form',
                    'type': 'object',
                    'icon': 'fa-external-link',
                    'string': _('Open Product Form View'),
                    'groups': 'base.group_user',
                }))

            # make tree view editable
            for node in doc.xpath("/tree"):
                node.set('edit', 'true')
                node.set('create', 'false')
                node.set('editable', 'top')
            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def write(self, vals):
        """
        Si en vals solo viene qty y force_product_edit entonces es un dummy
        write y lo hacemos con sudo
        """
        if len(vals) == 1 and vals.get('qty') and self._context.get(
                'force_product_edit'):
            self = self.sudo()
        return super(ProductProduct, self).write(vals)

    @api.multi
    def _compute_qty(self):
        sale_order_id = self._context.get('active_id', False)
        for rec in self:
            qty = 0
            if sale_order_id:
                lines = self.env['sale.order.line'].search([
                    ('order_id', '=', sale_order_id),
                    ('product_id', '=', rec.id)])
                qty = sum([line.product_uom._compute_quantity(
                    line.product_uom_qty,
                    rec.uom_id) for line in lines])
            rec.update({'qty': qty})

    @api.multi
    def _inverse_qty(self):
        sale_order_id = self._context.get('active_id', False)
        for rec in self:
            qty = rec.qty
            if sale_order_id:
                lines = self.env['sale.order.line'].search([
                    ('order_id', '=', sale_order_id),
                    ('product_id', '=', rec.id)])
                if lines:
                    (lines - lines[0]).unlink()
                    lines[0].write({
                        'product_uom_qty': qty,
                        'product_uom': rec.uom_id.id,
                    })
                else:
                    self.env['sale.order'].browse(
                        sale_order_id).add_products(rec.id, qty)

    @api.multi
    def action_product_form(self):
        self.ensure_one()
        view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'product.product_normal_form_view')
        return {
            'name': _('Product'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            # 'domain': [('id', 'in', self.apps_product_ids.ids)],
            'res_id': self.id,
            'view_id': view_id,
        }

    @api.multi
    def action_product_add_one(self):
        for rec in self:
            rec.qty += 1
