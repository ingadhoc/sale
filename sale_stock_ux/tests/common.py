##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Configuración de escenario de las suites de sale_stock_ux.

Hereda dos cosas distintas y a propósito:

- **`SaleUxCommon`** (`sale_ux`): plan de cuentas, partners y producto
  facturado por lo pedido. Es el entorno de venta, y ya existía.
- **`StockUxInvariants`** (`stock_ux`): la batería de invariantes de stock,
  que corre en todas las suites de la cadena.

Encima suma las dos invariantes que leen campos que define *este* módulo, y
los helpers de escenario. Las tres categorías de datos siguen separadas:
entorno de la base, configuración del escenario creada acá, y documentos
siempre creados por cada test.
"""

from odoo import Command
from odoo.addons.sale_ux.tests.common import SaleUxCommon
from odoo.addons.stock_ux.tests.invariants import StockUxInvariants
from odoo.tests import Form

# Un flujo de venta solo puede generar entregas y, en almacenes multi-paso,
# las patas internas que las alimentan. Es el conjunto que declara este módulo
# para la invariante parametrizada que vive en stock_ux.
SALE_FLOW_CODES = ("outgoing", "internal")


class SaleStockUxCommon(StockUxInvariants, SaleUxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        # sale_exception, cuando está instalado, bloquea confirmaciones con
        # reglas que son de la base y no del escenario bajo prueba
        if cls.env["sale.order"]._fields.get("ignore_exception"):
            cls.env["exception.rule"].search([("active", "=", True)]).write({"active": False})
        # Mercadería con seguimiento de inventario: la necesitan los escenarios
        # que reservan, y con stock cargado para no dejar disponible negativo
        cls.storable_product = cls.env["product.product"].create(
            {
                "name": "Sale Stock UX Storable",
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "order",
                "list_price": 100.0,
                "taxes_id": [Command.clear()],
            }
        )
        cls._poner_stock(cls.storable_product, 500.0)

    @classmethod
    def _poner_stock(cls, product, cantidad, location=None):
        """Deja stock disponible del producto en la ubicación indicada."""
        cls.env["stock.quant"]._update_available_quantity(product, location or cls.stock_location, cantidad)

    # -- helpers de escenario ------------------------------------------------

    @classmethod
    def _crear_orden_confirmada(cls, product=None, qty=10.0, **values):
        """Crea y confirma una orden de una línea del producto indicado."""
        order = cls._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": (product or cls.storable_product).id,
                        "product_uom_qty": qty,
                        "price_unit": 100.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ],
            **values,
        )
        order.action_confirm()
        return order

    def _entregar(self, picking, qty=None):
        """Valida la entrega, opcionalmente entregando menos que la demanda."""
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty if qty is None else qty
        picking.move_ids.picked = True
        picking._action_done()

    def _wizard_devolucion(self, picking, qty, to_refund):
        """Abre el wizard de devolución y setea cantidad y reembolso."""
        wizard = Form(
            self.env["stock.return.picking"].with_context(
                active_id=picking.id, active_ids=picking.ids, active_model="stock.picking"
            )
        ).save()
        wizard.product_return_moves.quantity = qty
        wizard.product_return_moves.to_refund = to_refund
        return wizard

    # -- invariantes propias de este módulo ----------------------------------

    def assert_all_qty_delivered_consistent(self, order):
        """``all_qty_delivered`` es siempre lo entregado más lo devuelto.

        Las dos cifras gobiernan a qué cantidad baja "cancelar remanente" y qué
        estado de entrega muestra la línea, así que un desfasaje entre ellas es
        lo que convierte una cantidad entregada correcta en una pedida errónea.
        """
        for line in order.order_line:
            self.assertEqual(
                line.product_uom_id.compare(line.all_qty_delivered, line.qty_delivered + line.quantity_returned),
                0,
                "Línea %s: all_qty_delivered %s != qty_delivered %s + quantity_returned %s"
                % (line.id, line.all_qty_delivered, line.qty_delivered, line.quantity_returned),
            )

    def assert_delivery_status_declared(self, order):
        """El estado de entrega es un valor declarado, y orden y líneas no se contradicen."""
        estados_orden = dict(self.env["sale.order"]._fields["delivery_status"]._description_selection(self.env))
        estados_linea = dict(self.env["sale.order.line"]._fields["delivery_status"]._description_selection(self.env))
        self.assertIn(
            order.delivery_status, estados_orden, "La orden %s tiene un estado de entrega no declarado" % order.name
        )
        for line in order.order_line:
            self.assertIn(
                line.delivery_status,
                estados_linea,
                "La línea %s tiene un estado de entrega no declarado" % line.id,
            )
        if order.delivery_status == "full":
            pendientes = order.order_line.filtered(lambda line: line.delivery_status == "to deliver")
            self.assertFalse(
                pendientes,
                "La orden %s dice entregada por completo y las líneas %s siguen por entregar"
                % (order.name, pendientes.ids),
            )

    def assert_bateria_venta(self, order):
        """Corre la batería entera contra una orden de venta.

        Se llama después de *cada* operación del escenario, no solo al final:
        los estados que esto ataja suelen verse un paso y quedar tapados por el
        siguiente.
        """
        self.assert_bateria_documento(order.picking_ids, SALE_FLOW_CODES)
        self.assert_all_qty_delivered_consistent(order)
        self.assert_delivery_status_declared(order)
