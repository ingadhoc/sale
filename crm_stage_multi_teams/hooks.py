##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

def post_init_hook(env):
    crm_stages = env['crm.stage'].search([('team_id', '!=', False)])
    for stage in crm_stages:
        stage.team_ids = [(4, stage.team_id.id)]
        stage.team_id = False
