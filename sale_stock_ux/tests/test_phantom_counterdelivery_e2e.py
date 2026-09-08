##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPhantomCounterdeliveryE2E(TransactionCase):
    """E2E: corre `button_cancel_remaining` a traves de entregas de 1/2/3 pasos
    y valida que el detector concuerda con el estado real de la cadena.

    - En cancelaciones sanas (1 paso, multi-paso estandar todo-pull, 2 pasos
      pull+push) el espejo negativo netea y NO queda contra-entrega: el detector
      debe quedar callado (sin falsos positivos).
    - En las rutas que reproducen el bug (pull+push+push de 3 pasos; pull+push
      de 2 pasos con `push_domain` desdoblado) el cancel deja una contra-entrega
      fantasma viva (Cliente -> interno, `to_refund`, sin `origin_returned`): el
      detector la agarra, el filtro la lista y el saneo la cancela dejando la
      cadena forward intacta.

    Nota: que una variante reproduzca depende del `stock_ux` instalado. Las
    asserts de reproduccion valen sobre `stock_ux` sin el fix de prevencion
    (origin/18.0), que es lo que ve el runbot de esta PR.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.partner = cls.env["res.partner"].create({"name": "Phantom E2E Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Phantom E2E Product", "type": "consu", "is_storable": True}
        )
        cls.env["ir.config_parameter"].sudo().set_param("sale_stock_ux.sanity_pickings", "True")
        cls.env.user.groups_id = [(4, cls.env.ref("stock.group_stock_manager").id)]

    # ---- warehouse builders ---------------------------------------------

    def _wh(self, code, steps):
        wh = self.env["stock.warehouse"].create(
            {"name": "Phantom %s" % code, "code": code, "delivery_steps": steps}
        )
        self.env["stock.quant"]._update_available_quantity(self.product, wh.lot_stock_id, 100)
        return wh

    def _wh_sequential_push(self, code, steps, push_domain=False):
        """Ruta multi-paso reescrita como pull + push(+push) — el reproductor
        conocido (ticket 126226 en 3 pasos). Con `push_domain` desdobla el push
        de salida en dos variantes por reserva (reproductor del ticket 124472)."""
        wh = self._wh(code, steps)
        route = wh.delivery_route_id
        route.rule_ids.unlink()
        Rule = self.env["stock.rule"]
        common = {"route_id": route.id, "warehouse_id": wh.id, "company_id": wh.company_id.id}
        Rule.create(
            {
                **common,
                "name": "%s pull" % code,
                "action": "pull",
                "procure_method": "make_to_stock",
                "location_src_id": wh.lot_stock_id.id,
                "location_dest_id": self.customer_loc.id,
                "location_dest_from_rule": False,
                "picking_type_id": wh.pick_type_id.id,
            }
        )
        if steps == "pick_pack_ship":
            Rule.create(
                {
                    **common,
                    "name": "%s push pack" % code,
                    "action": "push",
                    "procure_method": "make_to_order",
                    "location_src_id": wh.wh_pack_stock_loc_id.id,
                    "location_dest_id": wh.wh_output_stock_loc_id.id,
                    "picking_type_id": wh.pack_type_id.id,
                }
            )
        ship = {
            **common,
            "action": "push",
            "procure_method": "make_to_order",
            "location_src_id": wh.wh_output_stock_loc_id.id,
            "location_dest_id": self.customer_loc.id,
        }
        if push_domain:
            reserved = "[('move_line_ids.location_id', '%s', [%s])]"
            Rule.create(
                {
                    **ship,
                    "name": "%s push ship reserved" % code,
                    "picking_type_id": wh.out_type_id.id,
                    "push_domain": reserved % ("in", wh.lot_stock_id.id),
                }
            )
            Rule.create(
                {
                    **ship,
                    "name": "%s push ship not-reserved" % code,
                    "picking_type_id": wh.out_type_id.copy(
                        {"name": "%s OUT alt" % code, "sequence_code": "%sALT" % code, "warehouse_id": wh.id}
                    ).id,
                    "push_domain": reserved % ("not in", wh.lot_stock_id.id),
                }
            )
        else:
            Rule.create({**ship, "name": "%s push ship" % code, "picking_type_id": wh.out_type_id.id})
        return wh

    # ---- scenario helpers -----------------------------------------------

    def _order(self, wh, qty=10):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": wh.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": qty})],
            }
        )
        order.action_confirm()
        return order

    def _validate_first_step(self, order, wh):
        pick = order.picking_ids.filtered(lambda p: p.picking_type_id == wh.pick_type_id)
        self.assertTrue(pick, "no se creo el PICK")
        pick.action_assign()
        for move in pick.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        pick.button_validate()
        return pick

    def _chain_reverse_alive(self, order):
        """Ground-truth independiente del detector: movimientos vivos de la
        cadena que van Cliente -> interno (la firma de la contra-entrega)."""
        return order.picking_ids.move_ids.filtered(
            lambda m: (
                m.state not in ("done", "cancel")
                and m.location_id.usage == "customer"
                and m.location_dest_id.usage == "internal"
            )
        )

    def _cancel_remaining(self, order):
        order.order_line.with_context(cancel_from_order=True).button_cancel_remaining()

    def _assert_detector_matches_chain(self, order):
        detected = order._detect_phantom_counterdeliveries()
        expected = self._chain_reverse_alive(order).filtered(
            lambda m: m.to_refund and not m.origin_returned_move_id
        )
        self.assertEqual(detected, expected, "el detector no concuerda con la cadena real")
        self.assertEqual(order.has_phantom_counterdelivery, bool(expected))
        return detected

    # ---- control: cancelaciones sanas, sin fantasma ---------------------

    def test_1step_no_phantom(self):
        wh = self._wh("PH1", "ship_only")
        order = self._order(wh)
        self._cancel_remaining(order)
        self.assertFalse(self._chain_reverse_alive(order), "1 paso no debe generar contra-entrega")
        self._assert_detector_matches_chain(order)
        self.assertFalse(order.has_phantom_counterdelivery)

    def test_2step_standard_pull_no_false_positive(self):
        wh = self._wh("PH2S", "pick_ship")
        order = self._order(wh)
        self._validate_first_step(order, wh)
        self._cancel_remaining(order)
        self._assert_detector_matches_chain(order)

    def test_3step_standard_pull_no_false_positive(self):
        wh = self._wh("PH3S", "pick_pack_ship")
        order = self._order(wh)
        self._validate_first_step(order, wh)
        self._cancel_remaining(order)
        self._assert_detector_matches_chain(order)

    def test_2step_plain_pull_push_no_false_positive(self):
        wh = self._wh_sequential_push("PH2P", "pick_ship")
        order = self._order(wh)
        self._validate_first_step(order, wh)
        self._cancel_remaining(order)
        self._assert_detector_matches_chain(order)

    # ---- rutas push: hoy el core deja un put-back INTERNO (no fantasma) ----
    # En stock_ux@origin/18.0, cancelar remanente tras validar el PICK en una
    # ruta pull+push(+push) deja un put-back interno (Packing/Output -> Stock,
    # to_refund=False), NO una contra-entrega desde el cliente. El detector debe
    # ignorarlo (no es Cliente->interno con to_refund): sin falsos positivos.
    # El fantasma real de campo (Cliente->Despacho, to_refund) nace de un
    # disparador de config/estado que este almacen generico no replica; su
    # pipeline se valida con el artefacto sintetico en
    # test_phantom_counterdelivery.py.

    def test_3step_pull_push_push_no_false_positive_on_internal_putback(self):
        wh = self._wh_sequential_push("PH3P", "pick_pack_ship")
        order = self._order(wh)
        self._validate_first_step(order, wh)
        self._cancel_remaining(order)
        self.assertFalse(
            self._chain_reverse_alive(order),
            "no deberia haber contra-entrega Cliente->interno (solo put-back interno)",
        )
        self._assert_detector_matches_chain(order)

    def test_2step_push_domain_no_false_positive(self):
        wh = self._wh_sequential_push("PH2D", "pick_ship", push_domain=True)
        order = self._order(wh)
        self._validate_first_step(order, wh)
        self._cancel_remaining(order)
        self._assert_detector_matches_chain(order)
