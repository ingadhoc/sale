##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import tagged

from .common import SaleStockUxCommon


@tagged("post_install", "-at_install")
class TestStockInfo(SaleStockUxCommon):
    """Información de stock que el módulo muestra en la línea de venta.

    Cubre los comportamientos 20 y 21 del relevamiento. Lo que el test va a
    buscar es la conversión de unidad: una línea en docenas sobre un producto
    que se lleva en unidades.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Sub-ubicación marcada para mostrar stock: la configuración del
        # escenario la crea el test, no se hereda de la base
        cls.estanteria = cls.env["stock.location"].create(
            {
                "name": "Estantería Sale Stock UX",
                "location_id": cls.stock_location.id,
                "usage": "internal",
                "show_stock_on_products": True,
            }
        )
        cls.producto_en_unidades = cls.env["product.product"].create(
            {
                "name": "Sale Stock UX Por Unidad",
                "type": "consu",
                "is_storable": True,
                "uom_id": cls.product_uom_unit.id,
                "list_price": 10.0,
                "taxes_id": [Command.clear()],
            }
        )
        cls._poner_stock(cls.producto_en_unidades, 24.0, location=cls.estanteria)

    def _linea_en_docenas(self, qty=1.0):
        order = self._create_sale_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.producto_en_unidades.id,
                        "product_uom_qty": qty,
                        "product_uom_id": self.product_uom_pack.id,
                        "price_unit": 120.0,
                        "tax_ids": [Command.clear()],
                    }
                )
            ]
        )
        return order

    def test_el_stock_por_ubicacion_se_expresa_en_la_unidad_de_la_linea(self):
        """24 unidades en la estantería son 2 docenas para una línea en docenas."""
        order = self._linea_en_docenas()

        texto = order.order_line.stock_by_location or ""

        self.assertIn(self.estanteria.display_name, texto, "Tiene que listar la ubicación marcada")
        self.assertIn("2.00", texto, "24 unidades son 2 docenas: sin conversión diría 24.00")

    def test_las_ubicaciones_no_marcadas_no_se_listan(self):
        """Solo salen las ubicaciones con la marca encendida."""
        sin_marcar = self.env["stock.location"].create(
            {
                "name": "Depósito oculto Sale Stock UX",
                "location_id": self.stock_location.id,
                "usage": "internal",
                "show_stock_on_products": False,
            }
        )
        self._poner_stock(self.producto_en_unidades, 60.0, location=sin_marcar)
        order = self._linea_en_docenas()

        self.assertNotIn(sin_marcar.display_name, order.order_line.stock_by_location or "")

    def test_lo_reservado_sale_del_almacen_de_la_orden_incluyendo_sub_ubicaciones(self):
        """La reserva vive en una sub-ubicación y tiene que contarse igual."""
        order = self._linea_en_docenas(qty=1.0)
        order.action_confirm()
        order.picking_ids.action_assign()
        reservado = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.producto_en_unidades.id),
                ("location_id", "child_of", self.warehouse.lot_stock_id.id),
            ]
        )
        total_reservado = sum(reservado.mapped("reserved_quantity"))
        self.assertGreater(total_reservado, 0.0, "El escenario necesita una reserva viva")

        self.assertEqual(order.order_line.total_reserved_quantity, total_reservado)
