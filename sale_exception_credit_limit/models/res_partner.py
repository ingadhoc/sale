##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ============================================
    # CAMPOS AUXILIARES
    # ============================================

    is_branch_company = fields.Boolean(
        string='Is Branch Company',
        compute='_compute_is_branch_company',
        help="Indicates if the current company is a branch (has parent)",
    )

    @api.depends_context('company')
    def _compute_is_branch_company(self):
        """Detecta si la compañía actual tiene parent (es branch)"""
        for rec in self:
            rec.is_branch_company = bool(self.env.company.parent_id)

    # ============================================
    # use_partner_credit_limit con herencia
    # ============================================

    use_partner_credit_limit = fields.Boolean(
        string='Use Partner Credit Limit',
        compute='_compute_use_partner_credit_limit',
        inverse='_inverse_use_partner_credit_limit',
        store=True,
        readonly=False,
        company_dependent=True,
        tracking=True,
        help="Enable credit limit validation for this partner",
    )

    use_partner_credit_limit_own = fields.Boolean(
        string='Use Partner Credit Limit Own',
        company_dependent=True,
        help="Use credit limit set specifically for this company",
    )

    @api.depends('use_partner_credit_limit_own', 'company_id', 'company_id.parent_id')
    @api.depends_context('company')
    def _compute_use_partner_credit_limit(self):
        """Heredar del padre si no está seteado en la compañía actual"""
        for rec in self:
            current_company = self.env.company

            # Si tiene un valor propio en esta compañía, usarlo
            if rec.use_partner_credit_limit_own:
                rec.use_partner_credit_limit = True
            else:
                # Buscar en la jerarquía de padres
                use_limit = False
                company = current_company

                while company:
                    limit_own = rec.with_company(company).use_partner_credit_limit_own
                    if limit_own:
                        use_limit = True
                        break
                    company = company.parent_id

                rec.use_partner_credit_limit = use_limit

    def _inverse_use_partner_credit_limit(self):
        """Guardar el valor solo si es ROOT company"""
        for rec in self:
            current_company = self.env.company
            # Solo permitir guardar si es ROOT (no tiene parent)
            if not current_company.parent_id:
                rec.use_partner_credit_limit_own = rec.use_partner_credit_limit
            # Si es child, no hacer nada (readonly de facto)

    # ============================================
    # credit_limit con herencia
    # ============================================

    credit_limit = fields.Float(
        string='Credit Limit',
        compute='_compute_credit_limit',
        inverse='_inverse_credit_limit',
        store=True,
        readonly=False,
        tracking=True,
        company_dependent=True,
        help="Credit limit for this partner. Inherited from parent company if not set.",
    )

    credit_limit_own = fields.Float(
        string='Credit Limit Own',
        company_dependent=True,
        help="Credit limit set specifically for this company",
    )

    @api.depends('credit_limit_own', 'company_id', 'company_id.parent_id')
    @api.depends_context('company')
    def _compute_credit_limit(self):
        """Heredar del padre si no está seteado en la compañía actual"""
        for rec in self:
            current_company = self.env.company

            # Si tiene un valor propio en esta compañía, usarlo
            if rec.credit_limit_own:
                rec.credit_limit = rec.credit_limit_own
            else:
                # Buscar en la jerarquía de padres
                credit_limit = 0.0
                company = current_company

                while company:
                    limit = rec.with_company(company).credit_limit_own
                    if limit:
                        credit_limit = limit
                        break
                    company = company.parent_id

                rec.credit_limit = credit_limit

    def _inverse_credit_limit(self):
        """Guardar el valor solo si es ROOT company"""
        for rec in self:
            current_company = self.env.company
            # Solo permitir guardar si es ROOT (no tiene parent)
            if not current_company.parent_id:
                rec.credit_limit_own = rec.credit_limit
            # Si es child, no hacer nada (readonly de facto)

    # ============================================
    # CAMPOS EXISTENTES
    # ============================================

    credit_with_confirmed_orders = fields.Monetary(
        compute="_compute_credit_with_confirmed_orders",
        string="Credit Taken",
        help="Total amount this customer owes you (including not invoiced confirmed sale orders and draft invoices).",
        groups="account.group_account_invoice,account.group_account_readonly",
    )

    user_credit_config = fields.Boolean(
        compute="_compute_user_credit_config",
        string="User Credit Config",
    )

    # ============================================
    # MÉTODOS HELPER PARA JERARQUÍA
    # ============================================

    def _get_company_hierarchy(self, company):
        """Obtiene la jerarquía completa de compañías (root + todas las hijas)"""
        # Encontrar la root company
        root = company
        while root.parent_id:
            root = root.parent_id

        # Retornar root + todas sus hijas recursivamente
        return root | self._get_all_children(root)

    def _get_all_children(self, company):
        """Método recursivo para obtener TODAS las hijas"""
        children = self.env['res.company']
        for child in company.child_ids:
            children |= child
            children |= self._get_all_children(child)
        return children

    # ============================================
    # MÉTODOS COMPUTE
    # ============================================

    @api.depends_context("uid")
    def _compute_user_credit_config(self):
        """Verifica si el usuario tiene permisos para configurar límite de crédito"""
        self.user_credit_config = self.env.user.has_group("sale_exception_credit_limit.credit_config")

    @api.depends_context("company")
    def _compute_credit_with_confirmed_orders(self):
        """Calcula la deuda consolidada de toda la jerarquía de compañías"""
        for rec in self:
            # Set to 0 if use_partner_credit_limit is not enabled to avoid unnecessary computations
            if not rec.use_partner_credit_limit:
                rec.credit_with_confirmed_orders = 0
            else:
                current_company = self.env.company

                # Obtener jerarquía de compañías (root + todas las hijas)
                company_hierarchy = rec._get_company_hierarchy(current_company)

                to_invoice_amount = 0.0
                draft_invoice_lines_amount = 0.0
                total_credit = 0.0

                # Iterar sobre cada compañía de la jerarquía
                for company in company_hierarchy:
                    # ============================================
                    # 1. ÓRDENES DE VENTA CONFIRMADAS (por compañía)
                    # ============================================
                    order_domain = [
                        ("order_id.partner_id.commercial_partner_id", "=", rec.commercial_partner_id.id),
                        ("order_id.company_id", "=", company.id),  # Filtrar por compañía
                        ("invoice_status", "in", ["to invoice", "no"]),
                        ("order_id.state", "in", ["sale", "done"]),
                    ]
                    order_lines = rec.env["sale.order.line"].sudo().search(order_domain)

                    # Sum the amounts from all approved sale orders for order lines that are not yet invoiced
                    for line in order_lines:
                        # not_invoiced differs from the native qty_to_invoice:
                        # qty_to_invoice only considers lines ready to be invoiced according to the invoicing policy,
                        # while not_invoiced considers all lines regardless of delivery or readiness.
                        not_invoiced = line.product_uom_qty - line.qty_invoiced
                        if rec.env["sale.order.line"]._fields.get("quantity_returned"):
                            not_invoiced -= line.quantity_returned
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_ids.compute_all(
                            price,
                            line.order_id.currency_id,
                            not_invoiced,
                            product=line.product_id,
                            partner=line.order_id.partner_id,
                        )
                        total = taxes["total_included"]
                        # Asumir misma moneda en jerarquía (no hay conversión)
                        to_invoice_amount += total

                    # ============================================
                    # 2. FACTURAS DRAFT (por compañía)
                    # ============================================
                    draft_domain = [
                        ("move_id.partner_id.commercial_partner_id", "=", rec.commercial_partner_id.id),
                        ("move_id.company_id", "=", company.id),  # Filtrar por compañía
                        ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                        ("move_id.state", "=", "draft"),
                        # Include lines without sale_line_ids or those whose related sale order is fully invoiced
                        "|",
                        ("sale_line_ids", "=", False),
                        ("sale_line_ids.order_id.invoice_status", "=", "invoiced"),
                    ]
                    draft_invoice_lines = rec.env["account.move.line"].sudo().search(draft_domain)

                    for line in draft_invoice_lines:
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_ids.compute_all(
                            price,
                            line.move_id.currency_id,
                            line.quantity,
                            product=line.product_id,
                            partner=line.move_id.partner_id,
                        )
                        total = taxes["total_included"]
                        # Asumir misma moneda en jerarquía (no hay conversión)
                        draft_invoice_lines_amount += total

                    # ============================================
                    # 3. CRÉDITO CONTABLE (por compañía)
                    # ============================================
                    credit = rec.sudo().with_company(company).credit
                    # Asumir misma moneda en jerarquía (no hay conversión)
                    total_credit += credit

                # Total consolidado de toda la jerarquía
                rec.credit_with_confirmed_orders = to_invoice_amount + draft_invoice_lines_amount + total_credit

    # ============================================
    # MÉTODOS OVERRIDE
    # ============================================

    def write(self, vals):
        """
        Si esta constraint trae dolores de cabeza la podemos sacar ya que este "bache" 
        de seguridad esta en muchos lugares aún mas criticos. 
        Es un problema del ORM donde mucho se protege a nivel vista
        """
        if "credit_limit" in vals or "use_partner_credit_limit" in vals:
            for record in self:
                if not self.env.user.has_group("sale_exception_credit_limit.credit_config"):
                    new_credit_limit = vals.get("credit_limit", record.credit_limit)
                    if not record.parent_id or new_credit_limit != record.parent_id.credit_limit:
                        raise ValidationError(
                            "People without Credit limit Configuration Rights cannot modify credit limit parameters"
                        )
        return super().write(vals)
