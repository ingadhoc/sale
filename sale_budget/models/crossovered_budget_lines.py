from odoo import models, fields, api, _


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    def _compute_practical_amount(self):
        # por ahora es prueba de concepto y hacemos override
        # TODO mejorar y hacer herencia (viendo el dif con metodo super)
        for line in self:
            acc_ids = line.general_budget_id.account_ids.ids
            product_ids = line.general_budget_id.product_ids.ids
            date_to = line.date_to
            date_from = line.date_from
            if line.analytic_account_id.id:
                analytic_line_obj = self.env['account.analytic.line']
                domain = [('account_id', '=', line.analytic_account_id.id),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to),
                          ]
                if acc_ids:
                    domain += [('general_account_id', 'in', acc_ids)]
                if product_ids:
                    domain += [('product_id', 'in', product_ids)]

                where_query = analytic_line_obj._where_calc(domain)
                analytic_line_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT SUM(amount) from " + from_clause + " where " + where_clause

            else:
                aml_obj = self.env['account.move.line']
                domain = [
                          ('date', '>=', date_from),
                          ('date', '<=', date_to),
                          ('move_id.state', '=', 'posted')
                          ]
                if acc_ids:
                    domain += [('general_account_id', 'in', acc_ids)]
                if product_ids:
                    domain += [('product_id', 'in', product_ids)]
                where_query = aml_obj._where_calc(domain)
                aml_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

            self.env.cr.execute(select, where_clause_params)
            line.practical_amount = self.env.cr.fetchone()[0] or 0.0

    def action_open_budget_entries(self):
        if self.analytic_account_id:
            # if there is an analytic account, then the analytic items are loaded
            action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
            action['domain'] = [('account_id', '=', self.analytic_account_id.id),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
            if self.general_budget_id:
                domain = []
                acc_ids = line.general_budget_id.account_ids.ids
                product_ids = line.general_budget_id.product_ids.ids
                if acc_ids:
                    domain += [('general_account_id', 'in', acc_ids)]
                if product_ids:
                    domain += [('product_id', 'in', product_ids)]
                action['domain'] += domain
        else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
            domain = [
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to)
                ]
            acc_ids = line.general_budget_id.account_ids.ids
            product_ids = line.general_budget_id.product_ids.ids
            if acc_ids:
                domain += [('general_account_id', 'in', acc_ids)]
            if product_ids:
                domain += [('product_id', 'in', product_ids)]
            action['domain'] = domain
        return action

    planned_detail_ids = fields.One2many(
        "crossovered.budget.line.detail", "crossovered_budget_line_id", "Planned Detail"
    )
    planned_amount = fields.Monetary(
        'Planned Amount', required=True,
        compute='_compute_planned_amount', store=True, readonly=False)

    @api.depends(
        "planned_detail_ids.price_subtotal",
    )
    def _compute_planned_amount(self):
        for line in self.filtered('planned_detail_ids'):
            line.planned_amount = sum(
                x.price_subtotal for x in line.planned_detail_ids
            )

    # como onchange no va porque el .id no existe todavia, luego lo hacemos bien
    # TODO hacerlo de otra manera y no con onchange? computed store?
    # @api.onchange('general_budget_id')
    def expand_pack_line(self):
        if self.general_budget_id.product_ids:
            self.planned_detail_ids.unlink()
            # TODO agregar contexto de lista de precios
            # pricelist=self.order_id.pricelist_id.id
            for product in self.general_budget_id.product_ids:
                vals = {
                    "crossovered_budget_line_id": self.id,
                    "product_id": product.id,
                    "product_uom_qty": 1.0,
                    # TODO obtener precio y descuento con nuevo metodo
                    "price_unit": product.list_price,
                    # "discount": pack_line.sale_discount,
                }
                self.planned_detail_ids.create(vals)

    def action_assisted_pack_detail(self):
        view = self.env.ref("sale_budget.view_crossovered_budget_lines")
        if not self.planned_detail_ids:
            self.expand_pack_line()
        return {
            "name": _("Details"),
            "view_mode": "form",
            "res_model": "crossovered.budget.lines",
            "view_id": view.id,
            "type": "ir.actions.act_window",
            "target": "new",
            "readonly": True,
            "res_id": self.id,
            # "context": dict(self.env.context, pricelist=self.order_id.pricelist_id.id),
        }

    def button_save_data(self):
        return True
