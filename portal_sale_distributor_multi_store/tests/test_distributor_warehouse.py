##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestDistributorWarehouse(TransactionCase):
    """El pedido que carga un distribuidor del portal tiene que salir del almacén de
    su sucursal, no del que le corresponde al vendedor del cliente (ticket 127896)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.store = cls.env["res.store"].create({"name": "Sucursal distribuidor", "company_id": cls.company.id})
        cls.child_store = cls.env["res.store"].create(
            {"name": "Sucursal hija", "company_id": cls.company.id, "parent_id": cls.store.id}
        )
        cls.salesman_store = cls.env["res.store"].create({"name": "Sucursal vendedor", "company_id": cls.company.id})
        # sin sucursal y primero por secuencia: es el que elige el estándar
        cls.default_warehouse = cls.env.ref("stock.warehouse0")
        cls.default_warehouse.sequence = 1
        cls.store_warehouse = cls._create_warehouse("Almacén sucursal", "WHST", cls.store, 50)
        # con menos secuencia que el de la sucursal propia: no tiene que ganar
        cls.child_warehouse = cls._create_warehouse("Almacén sucursal hija", "WHCH", cls.child_store, 10)
        cls.salesman = cls.env["res.users"].create(
            {
                "name": "Vendedor del cliente",
                "login": "salesman_default_warehouse",
                "company_id": cls.company.id,
                "groups_id": [(4, cls.env.ref("sales_team.group_sale_salesman").id)],
                "store_ids": [(6, 0, (cls.salesman_store + cls.store + cls.child_store).ids)],
                "store_id": cls.salesman_store.id,
            }
        )
        cls.salesman.property_warehouse_id = cls.default_warehouse
        cls.distributor = cls._create_distributor(cls.store)
        cls.distributor.partner_id.user_id = cls.salesman
        cls.env["exception.rule"].search([("model", "in", ("sale.order", "sale.order.line"))]).write({"active": False})

    @classmethod
    def _create_warehouse(cls, name, code, store, sequence):
        return cls.env["stock.warehouse"].create(
            {
                "name": name,
                "code": code,
                "company_id": cls.company.id,
                "store_id": store.id,
                "sequence": sequence,
            }
        )

    @classmethod
    def _create_distributor(cls, store):
        return cls.env["res.users"].create(
            {
                "name": "Distribuidor %s" % (store.name if store else "sin sucursal"),
                "login": "distributor_%s" % (store.id if store else "no_store"),
                "company_id": cls.company.id,
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
                "store_ids": [(6, 0, store.ids)],
                "store_id": store.id if store else False,
            }
        )

    def _create_order(self, user):
        return self.env["sale.order"].with_user(user).create({"partner_id": user.partner_id.commercial_partner_id.id})

    def test_warehouse_comes_from_distributor_store(self):
        order = self._create_order(self.distributor)
        self.assertEqual(order.user_id, self.salesman)
        self.assertEqual(order.warehouse_id, self.store_warehouse)

    def test_distributor_without_store_keeps_standard_warehouse(self):
        """Sin sucursal no hay nada que forzar: las franquicias que trabajan así
        siguen saliendo del almacén que elige el estándar."""
        distributor = self._create_distributor(self.env["res.store"])
        distributor.partner_id.user_id = self.salesman
        order = self._create_order(distributor)
        self.assertEqual(order.warehouse_id, self.default_warehouse)

    def test_internal_user_with_store_keeps_standard_warehouse(self):
        """Un usuario interno tiene sucursal igual, así que lo que decide es el grupo
        de distribuidor y no la sucursal."""
        self.assertTrue(self.salesman.store_id)
        order = (
            self.env["sale.order"]
            .with_user(self.salesman)
            .create({"partner_id": self.distributor.partner_id.commercial_partner_id.id})
        )
        self.assertEqual(order.warehouse_id, self.default_warehouse)

    def test_recompute_by_internal_user_keeps_distributor_warehouse(self):
        """El almacén sale de quien creó el pedido, no de quien dispara el recálculo:
        si no, un interno que toca el pedido en borrador lo manda a otra sucursal."""
        order = self._create_order(self.distributor)
        order.with_user(self.salesman).write({"user_id": self.salesman.id})
        self.assertEqual(order.warehouse_id, self.store_warehouse)

    def test_child_store_warehouse_does_not_win(self):
        """El almacén de la sucursal propia gana sobre el de una sucursal hija, aunque
        la hija tenga menos secuencia."""
        order = self._create_order(self.distributor)
        self.assertNotEqual(order.warehouse_id, self.child_warehouse)
        self.assertEqual(order.warehouse_id, self.store_warehouse)
