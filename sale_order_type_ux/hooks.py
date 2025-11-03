##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale_order_type.models.account_move import AccountMove


def post_init_hook(env):
    default_sale_order_type = env.ref("sale_order_type_ux.default_sale_order_type")
    # usamos SQL directo para bypasear validaciones de Python (ej: sale_ux locked constraint)
    env.cr.execute(
        """
        UPDATE sale_order
        SET type_id = %s
        WHERE state IN ('sale', 'done')
          AND type_id IS NULL
    """,
        (default_sale_order_type.id,),
    )


def _revert_method(cls, name):
    """Revert the original method called ``name`` in the given class.
    See :meth:`~._patch_method`.
    """
    method = getattr(cls, name)
    setattr(cls, name, method.origin)


def uninstall_hook(env):
    _revert_method(AccountMove, "_compute_journal_id")
