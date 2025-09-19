from odoo import api
from odoo.addons.sale_order_type.models.account_move import AccountMove


def monkey_patches():
    @api.depends("sale_type_id")
    def _compute_journal_id(self):
        # Tengo que bypasear lo que hacia el sale order type para que en caso de
        # cruzamiento de compañia utilice el wizard de account multicompany ux
        res = super(AccountMove, self)._compute_journal_id()
        for move in self.filtered("sale_type_id.journal_id"):
            if move.sale_type_id.journal_id.company_id.id == move.company_id.id:
                move.journal_id = move.sale_type_id.journal_id
        return res

    def _patch_method(cls, name, method):
        origin = getattr(cls, name)
        method.origin = origin
        # propagate decorators from origin to method, and apply api decorator
        wrapped = api.propagate(origin, method)
        wrapped.origin = origin
        setattr(cls, name, wrapped)

    _patch_method(AccountMove, "_compute_journal_id", _compute_journal_id)
