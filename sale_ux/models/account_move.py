##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from collections import defaultdict

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

<<<<<<< 8e8b6f0db17248b0a42067b21acabdf75efbf73a
||||||| 913438a1ab98cbb01533257f86537b437eba8f71
    # dejamos este campo por si alguien lo usaba y ademas lo re usamos abajo
    sale_order_ids = fields.Many2many("sale.order", compute="_compute_sale_orders")
    # en la ui agregamos este que seria mejor a nivel performance
    has_sales = fields.Boolean(string="Has Sales?", compute="_compute_has_sales")

=======
    # dejamos este campo por si alguien lo usaba y ademas lo re usamos abajo
    sale_order_ids = fields.Many2many("sale.order", compute="_compute_sale_orders")
    # en la ui agregamos este que seria mejor a nivel performance
    has_sales = fields.Boolean(string="Has Sales?", compute="_compute_has_sales")
    # no almacenado: memoiza el calculo por factura, porque
    # _prepare_product_base_line_for_taxes_computation corre una vez por linea y necesita el
    # agregado de todas
    downpayment_base_targets = fields.Json(compute="_compute_downpayment_base_targets", exportable=False)

>>>>>>> 5007434fdcc1dc1687145a427f7845b66c03df2d
    @api.depends("move_type", "partner_id", "partner_id.lang", "company_id")
    def _compute_narration(self):
        """Override para respetar el parámetro propagate_note desde sale orders"""
        propagate_note = self.env["ir.config_parameter"].sudo().get_param("sale.propagate_note") == "True"

        # Si propagate_note está activado y la factura viene de una SO, no tocar la narración
        if propagate_note:
            invoices_from_so = self.filtered(lambda m: m.invoice_origin)
            invoices_to_compute = self - invoices_from_so
        else:
            invoices_to_compute = self

        # Aplicar la lógica original solo a facturas que no vienen de SO o cuando propagate_note=False
        if invoices_to_compute:
            super(AccountMove, invoices_to_compute)._compute_narration()

<<<<<<< 8e8b6f0db17248b0a42067b21acabdf75efbf73a
    # Evaluar en próximas versiones si Odoo lo resuelve
    def action_post(self):
        res = super(AccountMove, self).action_post()
        downpayment_lines = self.line_ids.sale_line_ids.filtered(lambda l: l.is_downpayment and not l.display_type)
        for downpayment_line in downpayment_lines:
            # When change currency in downpayment
            if self.currency_id != downpayment_line.currency_id:
                downpayment_invoice_line = self.invoice_line_ids.filtered(
                    lambda l: l.is_downpayment and l.sale_line_ids.ids == downpayment_line.ids
                )
                downpayment_invoice_line.ensure_one()
                price_unit = downpayment_invoice_line.price_unit
                converted_price_unit = self.currency_id._convert(
                    price_unit, downpayment_line.currency_id, self.company_id, self.invoice_date or fields.Date.today()
                )
                downpayment_line.price_unit = converted_price_unit
        return res
||||||| 913438a1ab98cbb01533257f86537b437eba8f71
    def _compute_sale_orders(self):
        for rec in self:
            rec.sale_order_ids = rec.invoice_line_ids.mapped("sale_line_ids.order_id")

    def _compute_has_sales(self):
        moves = self.filtered(lambda move: move.is_sale_document())
        (self - moves).has_sales = False
        for rec in moves:
            rec.has_sales = any(line for line in rec.invoice_line_ids.mapped("sale_line_ids"))
=======
    def _compute_sale_orders(self):
        for rec in self:
            rec.sale_order_ids = rec.invoice_line_ids.mapped("sale_line_ids.order_id")

    def _compute_has_sales(self):
        moves = self.filtered(lambda move: move.is_sale_document())
        (self - moves).has_sales = False
        for rec in moves:
            rec.has_sales = any(line for line in rec.invoice_line_ids.mapped("sale_line_ids"))

    @api.depends(
        "company_id",
        "company_id.tax_calculation_rounding_method",
        "currency_id",
        "invoice_line_ids.display_type",
        "invoice_line_ids.is_downpayment",
        "invoice_line_ids.price_unit",
        "invoice_line_ids.quantity",
        "invoice_line_ids.discount",
        "invoice_line_ids.tax_ids",
        "invoice_line_ids.account_id",
        "invoice_line_ids.product_id",
        "invoice_line_ids.product_uom_id",
        "invoice_line_ids.sale_line_ids",
    )
    def _compute_downpayment_base_targets(self):
        """Base sin impuestos objetivo de cada linea de producto de una factura que deduce un anticipo.

        El wizard de anticipos redondea el price_unit del anticipo a la moneda una vez por grupo
        (_prepare_down_payment_lines_values), asi que la factura final tiene que agregar y redondear
        las lineas de producto con esa misma particion para que la deduccion cancele exacto.

        Cada linea de anticipo de la factura trae la clave de su grupo puesta, asi que la partimos
        contra ella en lugar de re-derivarla. Un grupo puede tener mas de una linea de anticipo
        (pasa cuando se anticipo en varias tandas sobre la misma orden), y el objetivo sigue siendo
        el mismo: el agregado del grupo redondeado una sola vez. Si un grupo no tiene ninguna linea
        de anticipo que le corresponda, o si el anticipo del grupo quedo repartido en mas de una cuenta,
        no lo tocamos.

        Devuelve {str(line.id): base} solo para las lineas ajustadas, y vacio cuando no hay nada que
        corregir.
        """
        AccountTax = self.env["account.tax"]
        for move in self:
            move.downpayment_base_targets = False
            if not move.is_sale_document(include_receipts=True):
                # solo ventas: purchase tambien setea is_downpayment en sus lineas, y ahi la clave
                # de grupo no aplica (no hay sale_line_ids) ademas de no ser asunto de este modulo
                continue
            if move.company_id.tax_calculation_rounding_method != "round_globally":
                # con round_per_line cada linea ya se redondea sola y el residuo no aparece
                continue
            product_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == "product")
            downpayment_lines = product_lines.filtered("is_downpayment")
            if not downpayment_lines:
                continue
            downpayment_accounts_per_key = defaultdict(set)
            for line in downpayment_lines:
                key = move._get_downpayment_group_key(line)
                downpayment_accounts_per_key[key].add(line.account_id.id)
            currency = move.currency_id or move.company_id.currency_id
            # sin la clave de contexto el override devuelve la base cruda, que es lo que agregamos
            move_without_targets = move.with_context(sale_ux_downpayment_base_targets=False)
            raw_amounts_per_group = defaultdict(dict)
            for line in product_lines - downpayment_lines:
                base_line = move_without_targets._prepare_product_base_line_for_taxes_computation(line)
                AccountTax._add_tax_details_in_base_line(base_line, move.company_id)
                key = move._get_downpayment_group_key(line)
                raw_amounts_per_group[key][str(line.id)] = base_line["tax_details"]["raw_total_excluded_currency"]
            targets = {}
            for key, raw_amounts in raw_amounts_per_group.items():
                accounts = downpayment_accounts_per_key.get(key)
                if not accounts or len(accounts) > 1:
                    # sin un anticipo deducido para ese grupo no sabemos contra que cancela, y si el
                    # anticipo quedo repartido en mas de una cuenta la particion no es la nuestra: en
                    # los dos casos dejamos el redondeo estandar antes que arriesgar otro descuadre
                    continue
                rounded = {line_key: currency.round(amount) for line_key, amount in raw_amounts.items()}
                # el grupo se redondea una sola vez, como lo hizo el anticipo, y la diferencia la
                # absorbe la linea mas grande (mismo criterio que usa Odoo para distribuir deltas)
                delta = currency.round(sum(raw_amounts.values())) - sum(rounded.values())
                if not currency.is_zero(delta):
                    biggest = max(raw_amounts, key=lambda line_key: abs(raw_amounts[line_key]))
                    rounded[biggest] = currency.round(rounded[biggest] + delta)
                targets.update(rounded)
            move.downpayment_base_targets = targets

    def _get_downpayment_group_key(self, line):
        """Grupo con el que el wizard de anticipos redondeo la linea.

        Espeja la parte de _prepare_down_payment_lines_values que se puede reproducir sobre la
        factura: la orden y los impuestos (jerarquia aplanada y sin los fijos, que el anticipo no
        arrastra). El wizard tambien agrupa por cuenta, pero la que termina en la linea de anticipo
        no se puede re-derivar de forma confiable desde el producto, asi que en lugar de adivinarla
        se controla aparte que las lineas de anticipo del grupo compartan una sola.
        """
        self.ensure_one()
        taxes = line.tax_ids.flatten_taxes_hierarchy()
        fixed_taxes = taxes.filtered(lambda tax: tax.amount_type == "fixed")
        return (
            tuple(sorted(line.sale_line_ids.order_id.ids)),
            tuple(sorted((taxes - fixed_taxes).ids)),
        )

    # El core resuelve esto de forma nativa a partir de la 18.3: el motor de impuestos gano manejo
    # propio de anticipos (account.tax._prepare_down_payment_lines /
    # _prepare_base_lines_for_down_payment, verificado en 19.0) y setea el mismo
    # manual_total_excluded_currency que usamos aca. Este override es solo para 18.0 y NO tiene que
    # portearse a 19.0: ahi pisaria el valor que calcula el core.
    def _get_rounded_base_and_tax_lines(self, round_from_tax_lines=True):
        # El ajuste se activa solo por este camino, que es el que produce los importes contables de
        # la factura y sus totales. Los demas consumidores del hook por linea tienen que seguir
        # viendo la base cruda: el descuento por pronto pago escala el price_unit despues de armar
        # la base line, y varios EDI agregan un subconjunto de lineas, asi que una base fijada de
        # todo el grupo les daria un importe equivocado.
        move = self.with_context(sale_ux_downpayment_base_targets=True)
        return super(AccountMove, move)._get_rounded_base_and_tax_lines(round_from_tax_lines=round_from_tax_lines)

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        base_line = super()._prepare_product_base_line_for_taxes_computation(product_line)
        if not self.env.context.get("sale_ux_downpayment_base_targets"):
            return base_line
        target = (self.downpayment_base_targets or {}).get(str(product_line.id))
        if target is not None:
            # Con round_globally la linea de anticipo (ya redondeada cuando se facturo) se agrega
            # junto a las lineas de producto (en crudo), y el residuo sub-centavo del conjunto se
            # amplifica a un centavo entero: la factura final queda descuadrada contra la orden y,
            # si el anticipo la cubre entera, hasta se da vuelta a nota de credito. Apuntamos la
            # base del grupo al mismo numero que uso el anticipo. Eso corre el total_excluded de la
            # linea (y con el su saldo contable) en ese centavo, que es justamente el arreglo;
            # price_unit, price_subtotal y los importes crudos no se tocan.
            base_line["manual_total_excluded_currency"] = target
        return base_line
>>>>>>> 5007434fdcc1dc1687145a427f7845b66c03df2d
