from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "cancel_remaining_127378")
class TestCancelRemainingPartialReturn(TransactionCase):
    """Ticket 127378 (ricardoospital v18): cancelar remanente en una entrega
    MULTI-PASO con ruta de PUSH y ENTREGA PARCIAL deja tramos upstream
    (PICK/PACK) vivos en "esperando otra operacion", en vez de cancelarlos.

    A diferencia de 126226 (cancela con qty_delivered=0, estado limpio), aca
    parte del pedido ya salio al cliente (qty_delivered>0). El pick_pack_ship
    estandar es todo pull y NO reproduce, por eso replicamos la ruta pull+push+push
    (espejo de Aranguren/symmetria) que usan los almacenes del cliente.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.wh = cls.env["stock.warehouse"].create(
            {"name": "Test 127378", "code": "T378", "delivery_steps": "pick_pack_ship"}
        )
        pack_loc = cls.wh.wh_pack_stock_loc_id
        out_loc = cls.wh.wh_output_stock_loc_id
        route = cls.wh.delivery_route_id
        route.rule_ids.unlink()
        Rule = cls.env["stock.rule"]
        common = {"route_id": route.id, "warehouse_id": cls.wh.id, "company_id": cls.wh.company_id.id}
        cls.r_pick = Rule.create(
            {
                **common,
                "name": "TEST Stock -> Clientes (pull)",
                "action": "pull",
                "procure_method": "make_to_stock",
                "location_src_id": cls.wh.lot_stock_id.id,
                "location_dest_id": cls.customer_loc.id,
                "location_dest_from_rule": False,
                "picking_type_id": cls.wh.pick_type_id.id,
            }
        )
        cls.r_pack = Rule.create(
            {
                **common,
                "name": "TEST Zona -> Salida (push)",
                "action": "push",
                "procure_method": "make_to_order",
                "location_src_id": pack_loc.id,
                "location_dest_id": out_loc.id,
                "picking_type_id": cls.wh.pack_type_id.id,
            }
        )
        cls.r_ship = Rule.create(
            {
                **common,
                "name": "TEST Salida -> Clientes (push)",
                "action": "push",
                "procure_method": "make_to_order",
                "location_src_id": out_loc.id,
                "location_dest_id": cls.customer_loc.id,
                "picking_type_id": cls.wh.out_type_id.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Test Storable 127378", "type": "consu", "is_storable": True}
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.wh.lot_stock_id, 100)
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer 127378"})

    def _dump(self, so, label):
        lines = ["--- %s ---" % label]
        moves = self.env["stock.move"].search([("group_id", "=", so.procurement_group_id.id)], order="id")
        for m in moves:
            lines.append(
                "  move %s %-14s %s->%s final=%s qty=%s %s state=%s to_refund=%s"
                % (
                    m.id,
                    m.picking_id.name or "-",
                    m.location_id.name,
                    m.location_dest_id.name,
                    m.location_final_id.name or "-",
                    m.product_uom_qty,
                    m.procure_method,
                    m.state,
                    m.to_refund,
                )
            )
        return "\n".join(lines)

    def _validate(self, picking, qty=None):
        picking.action_assign()
        for move in picking.move_ids:
            move.move_line_ids.unlink()
            move.quantity = move.product_uom_qty if qty is None else qty
            move.picked = True
        action = picking.button_validate()
        if isinstance(action, dict) and action.get("res_model") == "stock.backorder.confirmation":
            self.env[action["res_model"]].with_context(**action["context"]).create({}).process()

    def _next(self, so, picking_type):
        return so.picking_ids.filtered(
            lambda p: p.picking_type_id == picking_type and p.state not in ("done", "cancel")
        )[:1]

    def _assert_no_internal_refund(self, so, report):
        """Ningun traslado interno->interno debe quedar marcado como devolucion
        (to_refund). El core lo hereda de la cantidad negativa; los put-backs
        internos del cancelar remanente no son devoluciones. Ticket 127378."""
        bad = so.order_line.move_ids.filtered(
            lambda m: m.to_refund and m.location_id.usage == "internal" and m.location_dest_id.usage == "internal"
        )
        self.assertFalse(
            bad,
            "BUG 127378: put-back interno marcado to_refund: %s\n%s"
            % (bad.mapped("picking_id.name"), "\n".join(report)),
        )

    def _make_return(self, picking, quantity, to_refund=True):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_ids=picking.ids, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.to_refund = to_refund
            line.quantity = quantity
        action = wizard.action_create_returns()
        ret = self.env["stock.picking"].browse(action["res_id"])
        self._validate(ret)
        return ret

    def _run(self, with_return):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 6})],
            }
        )
        so.action_confirm()
        report = [self._dump(so, "confirmada")]

        # PICK parcial 3/6 -> backorder de 3.
        self._validate(self._next(so, self.wh.pick_type_id), qty=3)
        report.append(self._dump(so, "PICK parcial 3/6"))
        # PACK y OUT de las 3 entregadas (push).
        self._validate(self._next(so, self.wh.pack_type_id))
        self._validate(self._next(so, self.wh.out_type_id))
        report.append(self._dump(so, "OUT 3 despachado"))
        self.assertEqual(so.order_line.qty_delivered, 3, "\n".join(report))

        if with_return:
            self._make_return(
                self._next(so, self.wh.out_type_id)
                or so.picking_ids.filtered(lambda p: p.state == "done" and p.picking_type_id == self.wh.out_type_id)[
                    :1
                ],
                quantity=1,
            )
            report.append(self._dump(so, "devolucion 1"))

        so.order_line.with_context(cancel_from_order=True).button_cancel_remaining()
        report.append(self._dump(so, "remanente cancelado"))
        self._assert_no_internal_refund(so, report)

    def test_partial_no_return(self):
        self._run(with_return=False)

    def test_partial_with_return(self):
        self._run(with_return=True)

    def test_partial_then_advance_remainder(self):
        """Entrega 3/6, y del remanente avanza el PICK del backorder (empuja un
        PACK que queda 'esperando otra operacion'), y recien ahi cancela
        remanente. Espejo del PACK huerfano del video (demanda 2)."""
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 6})],
            }
        )
        so.action_confirm()
        report = [self._dump(so, "confirmada")]

        # Entregar 3 completas por toda la cadena.
        self._validate(self._next(so, self.wh.pick_type_id), qty=3)
        self._validate(self._next(so, self.wh.pack_type_id))
        self._validate(self._next(so, self.wh.out_type_id))
        report.append(self._dump(so, "3 entregadas"))

        # Del remanente: validar el PICK del backorder -> empuja PACK (queda esperando).
        self._validate(self._next(so, self.wh.pick_type_id))
        report.append(self._dump(so, "PICK remanente validado (PACK empujado)"))

        so.order_line.with_context(cancel_from_order=True).button_cancel_remaining()
        report.append(self._dump(so, "remanente cancelado"))
        self._assert_no_internal_refund(so, report)
