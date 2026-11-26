##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestDistributorPartnerAccess(TransactionCase):
    """En pantalla chica el many2one de cliente abre la ventana «Buscar», que lee
    los contactos con la vista kanban de `res.partner` y pide `category_id`. Sin
    lectura sobre `res.partner.category` esa lectura falla entera y la ventana no
    se abre, así que el distribuidor no puede elegir el cliente de la cotización."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.distributor = cls.env["res.users"].create(
            {
                "name": "Distribuidor test",
                "login": "distributor_partner_access_test",
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

    def test_distributor_reads_the_partner_tags(self):
        partner = self.distributor.partner_id.with_user(self.distributor)
        # un AccessError acá es el fallo que estamos cubriendo
        self.assertEqual(partner.read(["category_id"])[0]["category_id"], [])
