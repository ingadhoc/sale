##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestDistributorStockAccess(TransactionCase):
    """`mrp_subcontracting` restringe varios modelos de stock sobre `base.group_portal`
    a lo que pertenece a la subcontratación del contacto. Un distribuidor no tiene
    nada de eso, así que sin reglas propias no puede ni cargar una línea (ticket
    127896)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.distributor = cls.env["res.users"].create(
            {
                "name": "Distribuidor test",
                "login": "distributor_stock_access_test",
                "company_id": cls.env.ref("base.main_company").id,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_portal").id,
                            cls.env.ref("portal_backend.group_portal_backend").id,
                            cls.env.ref("portal_sale_distributor.group_portal_backend_distributor").id,
                        ],
                    )
                ],
            }
        )

    def test_distributor_reads_the_stock_models(self):
        """Sin `mrp_subcontracting` no hay nada que probar: no existe la regla que
        restringe, y estas lecturas pasan igual."""
        if not self.env["ir.module.module"].search([("name", "=", "mrp_subcontracting"), ("state", "=", "installed")]):
            self.skipTest("mrp_subcontracting no está instalado")
        records = {
            "stock.location": self.warehouse.lot_stock_id,
            "stock.picking.type": self.warehouse.out_type_id,
            "stock.warehouse": self.warehouse,
            "stock.move": self.env["stock.move"].search([], limit=1),
            "stock.move.line": self.env["stock.move.line"].search([], limit=1),
        }
        for model, record in records.items():
            if not record:
                continue
            with self.subTest(model=model):
                # un AccessError acá es el fallo que estamos cubriendo
                self.assertTrue(record.with_user(self.distributor).display_name)
