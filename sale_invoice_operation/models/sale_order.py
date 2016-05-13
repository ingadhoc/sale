# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    operation_ids = fields.One2many(
        'sale.invoice.operation',
        'order_id',
        'Invoice Operations',
        readonly=True,
        copy=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
    )

    @api.one
    @api.constrains('invoice_ids')
    def add_operations_to_invoices(self):
        """
        If any invoice is append to sale order then we add operations if needed
        We also need to inherit make_invoices (of wizard) and _prepare_invoice
        because they originally write invoice_ids with sql
        """
        if self.operation_ids:
            for invoice in self.invoice_ids:
                if not invoice.operation_ids:
                    lines = invoice.invoice_line.ids
                    invoice.write({
                        'operation_ids': [(0, 0, x.with_context(
                            invoice_line_ids=lines).get_operations_vals())
                            for x in self.operation_ids]})

    @api.model
    def _prepare_invoice(self, order, lines):
        """
        Because some methods write invoice_ids by sql, we add this here.
        This method is not enaught because there are lot of ways to create an
        invoice linked to sale order and only a few call this method, we need
        also "add_operations_to_invoices"
        """
        vals = super(SaleOrder, self)._prepare_invoice(
            order, lines)
        # we send invoice_line_ids for compatibility with operation line
        vals['operation_ids'] = [
            (0, 0, x.with_context(
                invoice_line_ids=lines).get_operations_vals()) for x
            in order.operation_ids]
        return vals

    @api.multi
    def onchange_partner_id(self, partner_id):
        result = super(SaleOrder, self).onchange_partner_id(partner_id)
        if partner_id:
            partner = self.env['res.partner'].browse(
                partner_id).commercial_partner_id
            if partner.default_sale_invoice_plan:
                plan_vals = partner.default_sale_invoice_plan.get_plan_vals()
                result['value']['operation_ids'] = plan_vals
        return result

    @api.model
    def check_suspend_security_available(self):
        suspend_security = getattr(self, "suspend_security", None)
        if callable(suspend_security):
            return True
        return False

    @api.multi
    def action_done(self):
        """
        if we, for eg, pay an invoice and close sale order form a child
        company, then it would raise an error, we use suspend security
        """
        if self.check_suspend_security_available():
            return super(
                SaleOrder, self.suspend_security()).action_done()
        return super(SaleOrder, self.sudo()).action_done()

    @api.multi
    def action_invoice_end(self):
        """
        if we, for eg, pay an invoice and close sale order form a child
        company, then it would raise an error, we use suspend security
        """
        if self.check_suspend_security_available():
            return super(
                SaleOrder, self.suspend_security()).action_invoice_end()
        return super(SaleOrder, self.sudo()).action_invoice_end()
