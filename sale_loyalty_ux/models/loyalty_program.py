from odoo import fields, models


class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    def _get_valid_pricelists(self, pricelist):
        '''
        Returns a dict containing the pricelists that match per rule of the program
        '''
        rule_pricelists = dict()
        for rule in self.rule_ids:
            if not rule.pricelist_ids:
                rule_pricelists[rule] = pricelist
            else:
                rule_pricelists[rule] = rule.pricelist_ids
        return rule_pricelists
