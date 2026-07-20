from odoo.upgrade import util


def migrate(cr, version):
    """Refresh stock's return picking view so action_create_returns_all exists
    before loading our override.

    Odoo added that button to stock within the 18.0 series, but stock does not
    bump its manifest on a fix, so the view in DB may lack the button while our
    override already references it and fails to load. Force the base view refresh.
    """
    xmlid = "stock.view_stock_return_picking_form"
    util.update_record_from_xml(cr, xmlid, force_create=False)
