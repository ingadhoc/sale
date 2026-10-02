def post_init_hook(env):
    """Apply the "Identify Customer" default to the payment methods that already exist.

    Plain SQL because write() is forbidden on payment methods with an open session.
    """
    env.cr.execute("UPDATE pos_payment_method SET split_transactions = true WHERE split_transactions IS NOT TRUE")
    env["pos.payment.method"].invalidate_model(["split_transactions"])
