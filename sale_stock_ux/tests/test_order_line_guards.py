##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from .common import SaleStockUxCommon


@tagged("post_install", "-at_install")
class TestOrderLineGuards(SaleStockUxCommon):
    """Bloqueo de reducción de cantidad en una orden confirmada.

    Cubre el comportamiento 17 del relevamiento. Es un control positivo: lo
    que hay que verificar no es que avise, sino que la cantidad **no** cambie.
    """

    @mute_logger("odoo.tests.form.onchange")
    def test_no_se_puede_reducir_la_cantidad_de_una_orden_confirmada(self):
        order = self._crear_orden_confirmada(qty=10.0)

        with Form(order) as form:
            with form.order_line.edit(0) as linea:
                linea.product_uom_qty = 4.0

        self.assertEqual(
            order.order_line.product_uom_qty,
            10.0,
            "Reducir la cantidad tiene que revertirse: para bajarla va cancelar remanente",
        )

    def test_subir_la_cantidad_sigue_permitido(self):
        """Espejo: el bloqueo es solo hacia abajo."""
        order = self._crear_orden_confirmada(qty=10.0)

        with Form(order) as form:
            with form.order_line.edit(0) as linea:
                linea.product_uom_qty = 15.0

        self.assertEqual(order.order_line.product_uom_qty, 15.0)
        self.assert_bateria_venta(order)
