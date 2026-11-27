##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestDistributorPricelistAccess(TransactionCase):
    """Un distribuidor es un usuario externo: lee las listas de precios para cotizar,
    pero no puede cambiarlas. No hay regla de registro que acote la escritura a las
    listas del propio distribuidor, así que el permiso de escritura dejaba a cualquiera
    modificar las listas de la empresa por RPC."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.distributor = cls.env["res.users"].create(
            {
                "name": "Distribuidor test",
                "login": "distributor_pricelist_access_test",
                "company_id": cls.env.ref("base.main_company").id,
                "group_ids": [
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
        cls.pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Lista test",
                "item_ids": [(0, 0, {"compute_price": "fixed", "fixed_price": 10.0})],
            }
        )

    def test_distributor_reads_pricelists(self):
        pricelist = self.pricelist.with_user(self.distributor)
        self.assertEqual(pricelist.name, "Lista test")
        self.assertEqual(pricelist.item_ids.fixed_price, 10.0)

    def test_distributor_cannot_write_pricelist(self):
        with self.assertRaises(AccessError):
            self.pricelist.with_user(self.distributor).write({"name": "Cambiada"})

    def test_distributor_cannot_write_pricelist_item(self):
        with self.assertRaises(AccessError):
            self.pricelist.item_ids.with_user(self.distributor).write({"fixed_price": 1.0})
