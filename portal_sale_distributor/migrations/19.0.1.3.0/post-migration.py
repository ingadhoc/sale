from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    base_group = env.ref("portal_sale_distributor.group_portal_backend_distributor")
    if not base_group.privilege_id:
        openupgrade.load_data(
            env,
            "portal_sale_distributor",
            "security/portal_sale_distributor_security.xml",
        )
        base_group.invalidate_recordset()

        stock_group = env.ref("portal_sale_distributor.group_portal_backend_distributor_stock")
        missing_users = stock_group.user_ids - base_group.user_ids
        if missing_users:
            base_group.write({"user_ids": [(4, uid) for uid in missing_users.ids]})
