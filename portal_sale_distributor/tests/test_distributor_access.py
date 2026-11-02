##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestDistributorAccess(TransactionCase):
    """Los accesos del grupo distribuidor, que en 20 pasaron de `ir.rule` al dominio
    de `ir.access`. Cubre que ve las órdenes del árbol de su contacto comercial y no
    las de afuera, que puede crearlas, y que lee los contactos de sus compañías."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.commercial = cls.env["res.partner"].create({"name": "Distribuidora test"})
        cls.child = cls.env["res.partner"].create({"name": "Sucursal test", "parent_id": cls.commercial.id})
        cls.outsider = cls.env["res.partner"].create({"name": "Contacto ajeno test"})
        cls.distributor = cls.env["res.users"].create(
            {
                "name": "Distribuidor test",
                "login": "distributor_access_test",
                "company_id": cls.company.id,
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
        # the user's own contact hangs from the distributor, so commercial_partner_id is it
        cls.distributor.partner_id.parent_id = cls.commercial
        cls.order_in = cls.env["sale.order"].create({"partner_id": cls.child.id})
        cls.order_out = cls.env["sale.order"].create({"partner_id": cls.outsider.id})

    def test_distributor_accesses(self):
        orders = self.env["sale.order"].with_user(self.distributor)
        with self.subTest("ve las órdenes del árbol de su contacto comercial"):
            found = orders.search([("id", "in", (self.order_in + self.order_out).ids)])
            self.assertEqual(found, self.order_in)
        with self.subTest("no ve las de un contacto de afuera del árbol"):
            self.assertFalse(self.order_out.with_user(self.distributor).has_access("read"))
        with self.subTest("puede crear una orden para un contacto de su árbol"):
            created = orders.create({"partner_id": self.child.id})
            self.assertEqual(created.partner_id, self.child)
        with self.subTest("lee el contacto de su compañía"):
            # portal_res_partner_distributor_rule: in 19 it was a record rule that
            # ir-access dropped, re-added as a row of ir.access.csv. has_access is what
            # answers this: reading display_name returns a value either way.
            self.assertTrue(self.company.partner_id.with_user(self.distributor).has_access("read"))

    def test_distributor_pickings(self):
        """La fila de `stock.picking` sin dominio anulaba el filtro de portal de
        remitos: en la 20 los permisos de los grupos se suman con `Domain.OR`."""
        picking_type = self.env.ref("stock.picking_type_out")
        Picking = self.env["stock.picking"]
        own = Picking.create({"partner_id": self.distributor.partner_id.id, "picking_type_id": picking_type.id})
        outsider = Picking.create({"partner_id": self.outsider.id, "picking_type_id": picking_type.id})
        company_own = Picking.create({"partner_id": self.commercial.id, "picking_type_id": picking_type.id})
        with self.subTest("lee su propio remito"):
            self.assertTrue(own.with_user(self.distributor).has_access("read"))
        with self.subTest("lee el remito de su contacto comercial"):
            self.assertTrue(company_own.with_user(self.distributor).has_access("read"))
        with self.subTest("no lee el remito de un contacto ajeno"):
            self.assertFalse(outsider.with_user(self.distributor).has_access("read"))
        with self.subTest("no modifica el remito de un contacto ajeno"):
            self.assertFalse(outsider.with_user(self.distributor).has_access("write"))
