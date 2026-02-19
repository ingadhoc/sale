##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
def post_init_hook(env):
    default_sale_order_type = env.ref("sale_order_type_ux.default_sale_order_type")
    # usamos SQL directo para bypasear validaciones de Python (ej: sale_ux locked constraint)
    env.cr.execute(
        """
        UPDATE sale_order
        SET type_id = %s
        WHERE state IN ('sale', 'cancel')
          AND type_id IS NULL
    """,
        (default_sale_order_type.id,),
    )
<<<<<<< 43252cd02aa1fe6c706a976ef150f598a8e356ba
||||||| 966dc41c0e7846e295354deaf879bef06c9c9a6b


def _revert_method(cls, name):
    """Revert the original method called ``name`` in the given class.
    See :meth:`~._patch_method`.
    """
    method = getattr(cls, name)
    setattr(cls, name, method.origin)


def uninstall_hook(env):
    _revert_method(AccountMove, "_compute_journal_id")
=======


def _revert_method(cls, name):
    """Revert the original method called ``name`` in the given class.
    See :meth:`~._patch_method`.
    """
    method = getattr(cls, name)
    origin = getattr(method, "origin", None)
    if origin:
        setattr(cls, name, origin)


def uninstall_hook(env):
    _revert_method(AccountMove, "_compute_journal_id")
>>>>>>> 917efa734e1881011f99ca997400d4012b25e556
