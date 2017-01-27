# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning


class AccountInvoiceLineOperation(models.Model):
    _name = 'account.invoice.line.operation'

    display_name = fields.Char(
        compute='get_display_name'
    )
    operation_id = fields.Many2one(
        'account.invoice.operation',
        'Operation',
        required=True,
        ondelete='cascade',
        readonly=True,
        auto_join=True,
    )
    invoice_line_id = fields.Many2one(
        'account.invoice.line',
        'Invoice Line',
        ondelete='cascade',
        readonly=True,
        auto_join=True,
    )
    percentage = fields.Float(
        'Percentage',
        digits=dp.get_precision('Discount'),
    )

    @api.one
    @api.depends('operation_id.number', 'percentage')
    def get_display_name(self):
        self.display_name = "%s) %s%%" % (
            self.operation_id.number, self.percentage)

    @api.one
    @api.constrains('operation_id', 'percentage')
    def check_percetantage(self):
        return self._check_percetantage(
            'invoice_line_id',
            self.invoice_line_id.operation_line_ids,
            self.invoice_line_id.invoice_id.operation_ids)

    @api.one
    def _check_percetantage(self, line_field, operation_lines, operations):
        line_browse = getattr(self, line_field)
        # operation_lines = self.search([
        #     ('operation_id', '=', self.operation_id.id),
        #     (line_field, '=', line_browse.id)])
        amount_type = self.operation_id.amount_type
        if amount_type != 'percentage':
            raise Warning(_(
                'You can not create operation line for operation '
                'of amount type %s') % (amount_type))

        msg = _('Sum of percentage could not be greater than 100%')
        operation_lines.invalidate_cache()
        op_lines_percentage = sum(operation_lines.mapped('percentage'))
        if op_lines_percentage > 100.0:
            raise Warning(msg)

        # usamos esto para chequear si el saldo cumple con las restricciones
        # if line_field == 'invoice_line_id':
            # domain
        # balance_operation = self.operation_id.search([
        #     ('invoice_id', '=', model_record.id),
        #     ('amount_type', '=', 'balance')], limit=1)
        balance_operation = operations.filtered(
            lambda x: x.amount_type == 'balance')
        line_balance = 100.0 - op_lines_percentage

        # TODO we dont check it right now
        # disable this check for this group
        # if self.env.user.has_group(
        #         'account_invoice_operation.invoice_plan_edit'):
        #     return True
        restrictions = (
            line_browse.product_id.invoice_operation_restriction_id.detail_ids)
        for restriction in restrictions:
            # check restriction over a balance operation
            if (
                    (restriction.journal_id and
                        restriction.journal_id ==
                        balance_operation.journal_id) or
                    (restriction.company_id and
                        restriction.company_id ==
                        balance_operation.company_id)):
                if restriction.max_percentage < line_balance:
                    raise Warning(_(
                        'You can not use this percentages as balance operation'
                        ' "%s" for line "%s" will get a balance of "%s%%" and '
                        'it has a maximum restriction of %s%%') % (
                        balance_operation.display_name,
                        line_browse.product_id.name,
                        line_balance,
                        restriction.max_percentage))
            # chequeamos si la linea que se crea o se modifica esta en el rango
            # restringe si:
            # - restriccion tiene journal y es igual al de oper.
            # - restriccion tiene companya y es igual al de oper.
            if (
                    (restriction.journal_id and
                        restriction.journal_id ==
                        self.operation_id.journal_id) or
                    (restriction.company_id and
                        restriction.company_id ==
                        self.operation_id.company_id)):
                if self.percentage > restriction.max_percentage:
                    raise Warning(_(
                        'On product "%s", operation "%s" percentage can not be'
                        ' greater than %s%% because of a restriction') % (
                        line_browse.product_id.name,
                        self.operation_id.display_name,
                        restriction.max_percentage))


class AccountInvoiceOperation(models.Model):
    _inherit = 'account.invoice.operation'

    line_ids = fields.One2many(
        'account.invoice.line.operation',
        'operation_id',
        'Lines'
    )

    @api.multi
    def _run_checks(self):
        """
        This checks are called from an invoice when operations change
        We add checks that force product restrictions to be applied and then
        we call super checks (like percentage not greater than 100)
        """
        self.update_operations_lines(
            self.mapped('invoice_id.invoice_line'))
        return super(AccountInvoiceOperation, self)._run_checks()

    @api.multi
    def update_operations_lines(self, model_lines):
        """
        Esta funcion se llama de muchos lugares pare recomputar las lineas y
        generarlas si no existen.
        Segun desde donde se crean nos trae algunos inconvenientes para
        conservar el valor definido a mano en una sale order line
        Hay dos alternativas:
            Alternativa 1: pisamos las lineas (mantenemos perc si es posible)
            y borarmos solo las sin perc (podemos llamar sin problema a esta
            funcion)
            Altertnativa 2: borramos todas y las regeneramos, en este caso
            controlamos cuando se llama esta funcion
        El codigo referente a cada uno lo dejamos marcado antes con el nombre
        de la alternativa
        """
        if model_lines._name == 'sale.order.line':
            field = 'sale_line_id'
        elif model_lines._name == 'account.invoice.line':
            field = 'invoice_line_id'
        # Alternativa 2
        # delete old model_lines of self operations
        # model_lines.mapped('operation_line_ids').filtered(
        #     lambda x: x.operation_id.id in self.ids).unlink()
        for operation in self:
            # only create lines for amount_type percentage
            if operation.amount_type != 'percentage':
                # Alternativa 1
                # delete lines if they exist not percentage (if you change per
                # for balance for eg.)
                model_lines.mapped('operation_line_ids').filtered(
                    lambda x: x.operation_id.id == operation.id).unlink()
                continue
            for line in model_lines:
                # Altertnativa 1
                op_line = line.operation_line_ids.search([
                    ('operation_id', '=', operation.id),
                    (field, '=', line.id)], limit=1
                )
                if op_line:
                    percentage = op_line.percentage
                else:
                    percentage = operation.percentage

                restrictions = (
                    line.product_id.invoice_operation_restriction_id.detail_ids)
                for restriction in restrictions:
                    # restringe si:
                    # - restriccion tiene journal y es igual al de oper.
                    # - restriccion tiene companya y es igual al de oper.
                    if (
                            (restriction.journal_id and
                                restriction.journal_id ==
                                operation.journal_id) or
                            (restriction.company_id and
                                restriction.company_id ==
                                operation.company_id)):
                        # restriction min > perc, then rest min
                        # percentage = max(
                        #     percentage, restriction.min_percentage)
                        # restriction max < perc, then rest max
                        percentage = min(
                            percentage, restriction.max_percentage)

                vals = {
                    'operation_id': operation.id,
                    field: line.id,
                    'percentage': percentage,
                }

                # Altertnativa 1
                if op_line:
                    op_line.write(vals)
                else:
                    op_line.create(vals)
                # Altertnativa 2
                # line.operation_line_ids.create(vals)
