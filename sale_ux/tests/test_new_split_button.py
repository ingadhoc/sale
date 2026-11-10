from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestNewSplitButton(HttpCase):
    """With quotation templates the core makes the whole "New" button a dropdown. We split it:
    the text creates a quotation and the caret opens the menu. If a new Odoo changes the core
    template and our extension no longer applies, this tour is what breaks."""

    def test_new_button_is_split_in_two(self):
        self.env["sale.order.template"].create({"name": "Split button template", "template_type": "quotation"})

        self.start_tour(
            "/odoo/action-sale.action_quotations_with_onboarding", "sale_ux_new_split_button_tour", login="admin"
        )
