from odoo import models, fields


class MailActivityMixin(models.AbstractModel):
    _inherit = 'mail.activity.mixin'

    activity_ids = fields.One2many(
        groups="base.group_user, base.group_portal",
    )
