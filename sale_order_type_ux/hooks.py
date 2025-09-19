##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale_order_type.models.account_move import AccountMove


def post_init_hook(env):
    default_sale_order_type = env.ref("sale_order_type_ux.default_sale_order_type")
    sale_orders = env["sale.order"].search([("state", "in", ["sale", "done"])])
    sale_orders.write({"type_id": default_sale_order_type.id})


def _revert_method(cls, name):
    """Revert the original method called ``name`` in the given class.
    See :meth:`~._patch_method`.
    """
    method = getattr(cls, name)
    setattr(cls, name, method.origin)


def uninstall_hook(env):
    _revert_method(AccountMove, "_compute_journal_id")
