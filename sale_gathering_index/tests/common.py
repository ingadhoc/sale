from odoo.addons.sale_gathering.tests.common import SaleGatheringCommon


class SaleGatheringIndexCommon(SaleGatheringCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sale_exception_installed = cls.env["sale.order"]._fields.get("ignore_exception")
        if sale_exception_installed:
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})
