##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale_order_type_invoice_policy.tests.common import SaleOrderTypeInvoicePolicyCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestCampoDeAutorizacion(SaleOrderTypeInvoicePolicyCommon):
    """Lo que el campo promete además de liberar la salida: queda auditado y no se copia."""

    def _flush_tracking(self):
        self.env.flush_all()
        self.env.cr.precommit.run()

    def test_el_campo_de_autorizacion_se_declara_para_auditoria(self):
        order = self._order(self._sale_type("prepaid"))
        self._flush_tracking()

        with self.subTest("autorizarla queda registrada en el chatter"):
            previos = order.message_ids
            order.approve_picking = True
            self._flush_tracking()
            order.invalidate_recordset()
            etiqueta = order.fields_get(["approve_picking"])["approve_picking"]["string"]
            nuevos = order.message_ids - previos
            self.assertTrue(
                any(msg.message_type == "tracking" and etiqueta in (msg.body or "") for msg in nuevos),
                "tildar la autorización no dejó un mensaje de seguimiento en la venta",
            )

        with self.subTest("duplicar la venta no arrastra la autorización"):
            self.assertFalse(order.copy().approve_picking)
