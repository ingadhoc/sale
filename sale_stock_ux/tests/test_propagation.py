##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged

from .common import SaleStockUxCommon


@tagged("post_install", "-at_install")
class TestPropagation(SaleStockUxCommon):
    """Propagación de notas al remito y parámetro de unidad de medida.

    Cubre los comportamientos 26 y 31 del relevamiento. Los dos son
    configuración que gobierna un efecto, así que van juntos y parametrizados.
    """

    def _set_param(self, clave, valor):
        self.env["ir.config_parameter"].sudo().set_param(clave, valor)

    def test_las_notas_de_la_orden_viajan_al_remito_segun_el_parametro(self):
        for clave, campo_orden, campo_picking, texto in [
            ("sale.propagate_internal_notes", "internal_notes", "note", "Entregar por la puerta lateral"),
            ("sale.propagate_note", "note", "observations", "Condiciones acordadas con el cliente"),
        ]:
            with self.subTest("con el parámetro apagado la nota no viaja", clave=clave):
                self._set_param(clave, "False")
                order = self._crear_orden_confirmada(qty=5.0, **{campo_orden: f"<p>{texto}</p>"})
                self.assertNotIn(texto, str(order.picking_ids[campo_picking] or ""))

            with self.subTest("con el parámetro encendido la nota viaja al remito", clave=clave):
                self._set_param(clave, "True")
                order = self._crear_orden_confirmada(qty=5.0, **{campo_orden: f"<p>{texto}</p>"})
                self.assertIn(texto, str(order.picking_ids[campo_picking] or ""))
                self.assert_bateria_venta(order)

    def test_el_parametro_de_unidad_de_medida_va_y_vuelve(self):
        """Round-trip de propagate_uom contra ir.config_parameter."""
        Config = self.env["res.config.settings"]
        get_param = self.env["ir.config_parameter"].sudo().get_param

        with self.subTest("encendido guarda 1 y se relee encendido"):
            Config.create({"propagate_uom": True}).set_values()
            self.assertEqual(get_param("stock.propagate_uom"), "1")
            self.assertTrue(Config.new({}).get_values()["propagate_uom"])

        with self.subTest("apagado guarda 0 y se relee apagado"):
            Config.create({"propagate_uom": False}).set_values()
            self.assertEqual(get_param("stock.propagate_uom"), "0")
            self.assertFalse(Config.new({}).get_values()["propagate_uom"])
