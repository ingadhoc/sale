from odoo import models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _is_not_billed(self):
        """ Relativo a lo que esta en README en item c2
        Basicamente lo que hacemos es proteger las lineas de parte de horas si se setea ese parametro.
        Lo hacemos a traves de este campo que es llamado por todos los metodos que actualizan la info del parte de horas.
        De hecho de alguna manera estamos siguiendo misma logica de odoo que si esta billeado no deberia cambiarse.
        El tema es que en facturado a precio fijo no esta el concepto de billeado o no
        """
        self.ensure_one()
        protect_so_line = self._origin and self.env['ir.config_parameter'].sudo().get_param(
            'sale_timesheet_ux.protect_so_line', '')
        if protect_so_line:
            return False
        else:
            return super()._is_not_billed()
