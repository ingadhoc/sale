##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Quitamos el check_company ya que no permitira
    # realizar un cambio de compañia entre la venta y su factura de anticipo
    tax_id = fields.Many2many(check_company=False)

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        # Fix multicompañía:
        # Cuando se cambia la compañía de una factura de anticipo (ya sea con el wizard de "change company"
        # o mediante el sale order type), Odoo reutiliza la cuenta contable de esa factura de anticipo
        # para las siguientes facturas.
        # El problema es que el cambio de compañía recién se aplica al crear la factura en borrador,
        # por lo que la cuenta tomada no coincide con la compañía actual (de la venta).
        # Para evitarlo, se fuerza la cuenta que hubiera correspondido sin el cambio de compañía;
        # luego, el wizard se encarga de ajustar las cuentas según corresponda.
        downpayment_lines = self.invoice_lines.filtered("is_downpayment")
        account_id = res.get("account_id") and self.env["account.account"].browse(res["account_id"]) or None
        if (
            self.is_downpayment
            and downpayment_lines
            and account_id
            and self.company_id.id not in account_id.company_ids.ids
        ):
            company = self.order_id.type_id.journal_id.company_id
            acc = self.env["account.change.company"].create(
                {
                    "move_id": self.invoice_lines.move_id.id,
                    "company_ids": [self.company_id.id, company.id],
                    "company_id": self.company_id.id,
                    "journal_id": self.order_id.type_id.journal_id.id,
                }
            )
            account_id = acc._get_change_downpayment_account(self.invoice_lines, self.order_id.fiscal_position_id)
            res["account_id"] = account_id.id
        return res
