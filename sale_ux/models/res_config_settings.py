from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    analytic_account_without_company = fields.Boolean(
        "Crear proyecto y cuenta analitica sin compañia", config_parameter="sale_ux.analytic_account_without_company"
    )
    group_allow_any_user_as_salesman = fields.Boolean(
        "Allow any user as salesman", implied_group="sale_ux.group_allow_any_user_as_salesman"
    )
    show_product_image_on_report = fields.Boolean(
        string="Show Product Image", default=False, config_parameter="sale_ux.show_product_image_on_report"
    )
    dont_send_notes_to_invoices = fields.Boolean(
        string="Do not send notes to invoices", default=False, config_parameter="sale_ux.dont_send_notes_to_invoices"
    )

    # agregamos sale para que no se llame igual al de account
    group_sale_reference_on_tree_and_main_form = fields.Boolean(
        "Customer reference in list view and form",
        implied_group="sale_ux.group_reference_on_tree_and_main_form",
        # agregamos portal para portal distributor
        group="base.group_user,base.group_portal",
    )

    update_prices_automatically = fields.Boolean()

    move_internal_notes = fields.Boolean(
        "Mover notas internas a transferencias de stock y facturas",
    )
    move_note = fields.Boolean(
        "Mover términos y condiciones a transferencias de stock y facturas",
    )
    cancel_old_quotations = fields.Boolean(
        config_parameter="sale_ux.cancel_old_quotations", help="Enable automatic cancellation of old quotations."
    )
    days_to_keep_quotations = fields.Integer(
        string="Days to Keep Quotations",
        config_parameter="sale_ux.days_to_keep_quotations",
        help="Number of days to keep quotations before cancelling them.",
        default=30,
    )
    auto_select_all_documents = fields.Boolean(
        string="Auto-select all documents",
        config_parameter="sale_ux.auto_select_all_documents",
        help="Automatically select all available documents from PDF Quote Builder.",
        default=False,
    )
    group_delivery_date = fields.Boolean(
        "Show Delivery Date in Quotations report and online budget",
        implied_group="sale_ux.group_delivery_date_on_report_online",
    )

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env["ir.config_parameter"].sudo().get_param
        res.update(move_internal_notes=get_param("sale.propagate_internal_notes") == "True")
        res.update(move_note=get_param("sale.propagate_note") == "True")
        res.update(
            update_prices_automatically=get_param("sale_ux.update_prices_automatically", "False").lower() == "true"
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env["ir.config_parameter"].sudo().set_param
        set_param("sale.propagate_internal_notes", repr(self.move_internal_notes))
        set_param("sale.propagate_note", repr(self.move_note))
        set_param("sale_ux.update_prices_automatically", repr(self.update_prices_automatically))

    @api.constrains("days_to_keep_quotations")
    def _check_days_to_keep_sale_orders(self):
        for record in self:
            if record.days_to_keep_quotations <= 0:
                raise ValidationError(_("Days to keep quotations must be greater than 0."))
