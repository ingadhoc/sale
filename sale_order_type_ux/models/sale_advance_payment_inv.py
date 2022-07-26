##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, _


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    deposit_taxes_id = fields.Many2many(
        default=lambda self: self._default_deposit_taxes_id()
    )

    def _create_invoice(self, order, so_line, amount):
        """ Corregimos facturas de adelantos para dos casos:
        1. Al estar logueados en una cia pero que el pedido sea de cia hija
        2. al usar sale type con un journal de una cia hija
        En el caso de que haya posicion fiscal seteada y con compañia, la
        borramos momentaneamente porque el metodo de odoo "_create_invoice"
        no es heredable (Como el _prepare_invoice).
        """
        self.ensure_one()
        company_id = order.company_id.id
        if 'type_id' in order._fields and order.type_id.journal_id:
            company_id = order.type_id.journal_id.company_id.id

        order = order.with_company(company_id)
        self = self.with_company(company_id)
        original_fiscal_position_id = False
        if order.fiscal_position_id.company_id and order.\
                fiscal_position_id.company_id.id != company_id:
            original_fiscal_position_id = order.fiscal_position_id
            order.fiscal_position_id = False
        invoice = super()._create_invoice(
            order, so_line, amount)

        if original_fiscal_position_id:
            order.fiscal_position_id = original_fiscal_position_id
        return invoice
