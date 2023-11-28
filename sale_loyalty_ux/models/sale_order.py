from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def _program_check_compute_points(self, programs):
        res = super()._program_check_compute_points(programs)
        pricelist = self.pricelist_id
        pricelists_per_rule = programs._get_valid_pricelists(pricelist)
        aux_programs = programs
        for program in programs:
            aux_programs -= program
            for rule in program.rule_ids:
                if self.pricelist_id in pricelists_per_rule.get(rule):
                    aux_programs += program
                    break
        for r in res:
            if r not in aux_programs:
                res[r] = {'error': "pricelist not matching"}
        return res
