##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestDownpaymentRounding(AccountTestInvoicingCommon):
    """Facturas finales que deducen un anticipo bajo round_globally.

    Una cantidad decimal puede dejar el subtotal crudo de una linea en medio centavo
    (0.5 * 1.01 = 0.505), mientras que el anticipo solo pudo facturar el importe ya redondeado.
    Al agregar ambos lados, ese residuo se amplifica a un centavo entero que descuadra la factura
    final contra la orden, y cuando el anticipo cubre todo la da vuelta a nota de credito.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.tax_calculation_rounding_method = "round_globally"
        # sale_exception, presente al instalar el stack completo, hace cr.rollback() dentro de
        # action_confirm cuando detecta una excepcion: en un test eso se lleva puesta la
        # transaccion entera, no solo la confirmacion. Desactivamos las reglas para que el
        # escenario sea determinista.
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].sudo().search([]).write({"active": False})
        # 'consu' + invoice_policy 'order' es lo mas robusto en el stack completo: un 'service'
        # arrastra service_policy / subscription / timesheet y puede dejar la factura final sin
        # nada facturable. _create_product ya setea las cuentas de ingreso y gasto.
        cls.product_a_tax = cls._create_product(
            name="DP rounding tax A", type="consu", invoice_policy="order", taxes_id=cls.tax_sale_a
        )
        cls.product_b_tax = cls._create_product(
            name="DP rounding tax B", type="consu", invoice_policy="order", taxes_id=cls.tax_sale_b
        )

    def _create_order(self, lines):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": quantity,
                            "price_unit": price_unit,
                            "tax_id": [Command.set(product.taxes_id.ids)],
                        }
                    )
                    for product, quantity, price_unit in lines
                ],
            }
        )

    def _invoice_downpayment_and_balance(self, order, percentage):
        """Factura el anticipo, lo contabiliza y devuelve (anticipo, factura final)."""
        order.action_confirm()
        self.assertEqual(order.state, "sale", "la orden tiene que quedar confirmada")
        self.env["sale.advance.payment.inv"].with_context(
            active_model="sale.order", active_ids=order.ids, active_id=order.id
        ).create({"advance_payment_method": "percentage", "amount": percentage}).create_invoices()
        downpayment = order.invoice_ids
        downpayment.action_post()
        return downpayment, order._create_invoices(final=True)

    def _assert_no_spurious_refund(self, final_invoice):
        self.assertEqual(
            final_invoice.move_type,
            "out_invoice",
            "una factura final totalmente deducida no puede salir como nota de credito",
        )

    def test_full_downpayment_single_line(self):
        """Anticipo del 100% sobre una linea con residuo de medio centavo."""
        order = self._create_order([(self.product_a_tax, 0.5, 1.01)])
        downpayment, final_invoice = self._invoice_downpayment_and_balance(order, 100)

        self._assert_no_spurious_refund(final_invoice)
        self.assertAlmostEqual(final_invoice.amount_total, 0.0, places=2)
        self.assertAlmostEqual(downpayment.amount_total, order.amount_total, places=2)

    def test_full_downpayment_multiple_lines(self):
        """Varias lineas con residuo: el conjunto se redondea una sola vez, no linea por linea."""
        order = self._create_order([(self.product_a_tax, 0.5, 1.01)] * 3)
        downpayment, final_invoice = self._invoice_downpayment_and_balance(order, 100)

        self._assert_no_spurious_refund(final_invoice)
        self.assertAlmostEqual(final_invoice.amount_total, 0.0, places=2)
        self.assertAlmostEqual(
            downpayment.amount_total + final_invoice.amount_total,
            order.amount_total,
            places=2,
            msg="lo facturado no puede diferir del total de la orden",
        )

    def test_full_downpayment_many_lines(self):
        """El error crecia con la cantidad de lineas: cinco lineas, cinco residuos."""
        order = self._create_order([(self.product_a_tax, 0.5, 1.01)] * 5)
        downpayment, final_invoice = self._invoice_downpayment_and_balance(order, 100)

        self._assert_no_spurious_refund(final_invoice)
        self.assertAlmostEqual(final_invoice.amount_total, 0.0, places=2)
        self.assertAlmostEqual(downpayment.amount_total + final_invoice.amount_total, order.amount_total, places=2)

    def test_partial_downpayment_multiple_lines(self):
        """Anticipo parcial: la factura final cobra el resto exacto, sin centavo de mas."""
        order = self._create_order([(self.product_a_tax, 0.5, 1.01)] * 3)
        downpayment, final_invoice = self._invoice_downpayment_and_balance(order, 40)

        self.assertAlmostEqual(
            downpayment.amount_total + final_invoice.amount_total,
            order.amount_total,
            places=2,
            msg="anticipo + factura final tienen que sumar el total de la orden",
        )

    def test_full_downpayment_mixed_taxes(self):
        """Dos impuestos distintos: el anticipo se redondea una vez por combinacion de impuestos.

        La factura final tiene que agregar con esa misma particion. El anticipo puede quedar un
        centavo arriba del total de la orden (el wizard redondea por grupo y la orden agrega todo
        junto), pero eso es previo a este arreglo y no depende de la factura final: lo que se
        verifica aca es que la final cierre en cero y no salga nota de credito.
        """
        order = self._create_order([(self.product_a_tax, 0.5, 1.01), (self.product_b_tax, 0.5, 1.01)])
        downpayment, final_invoice = self._invoice_downpayment_and_balance(order, 100)

        self.assertEqual(len(downpayment.invoice_line_ids.filtered("is_downpayment")), 2)
        self._assert_no_spurious_refund(final_invoice)
        self.assertAlmostEqual(final_invoice.amount_total, 0.0, places=2)

    def test_full_downpayment_without_residual(self):
        """Sin residuo sub-centavo el comportamiento no cambia."""
        order = self._create_order([(self.product_a_tax, 1.0, 100.0)] * 3)
        downpayment, final_invoice = self._invoice_downpayment_and_balance(order, 30)

        self.assertAlmostEqual(downpayment.amount_untaxed, 90.0, places=2)
        self.assertAlmostEqual(final_invoice.amount_untaxed, 210.0, places=2)
        self.assertAlmostEqual(downpayment.amount_total + final_invoice.amount_total, order.amount_total, places=2)

    def test_round_per_line_is_not_adjusted(self):
        """Con round_per_line el ajuste no se activa.

        Ese metodo arrastra su propia diferencia de un centavo, por otro camino: el wizard suma los
        importes crudos y redondea una vez, mientras cada linea de la factura se redondea sola. No
        se corrige aca porque no produce la nota de credito que motiva este arreglo y tocarlo
        cambiaria el comportamiento del metodo de redondeo que Odoo usa por default. Lo que se
        verifica es que el ajuste quede inactivo y que no aparezca una nota de credito.
        """
        self.env.company.tax_calculation_rounding_method = "round_per_line"
        order = self._create_order([(self.product_a_tax, 0.5, 1.01)] * 3)
        dummy, final_invoice = self._invoice_downpayment_and_balance(order, 100)

        self.assertFalse(final_invoice.downpayment_base_targets)
        self._assert_no_spurious_refund(final_invoice)

    def test_full_downpayment_with_fixed_tax(self):
        """Un impuesto fijo en algunas lineas no tiene que partir el grupo.

        El anticipo no arrastra los impuestos fijos, asi que agrupa esas lineas junto con las que
        solo llevan el impuesto porcentual. Se compara la base sin impuestos porque el impuesto fijo
        se cobra recien en la factura final.
        """
        fixed_tax = self.env["account.tax"].create(
            {
                "name": "Fixed sale tax",
                "type_tax_use": "sale",
                "amount_type": "fixed",
                "amount": 1.0,
                "company_id": self.env.company.id,
            }
        )
        product_with_fixed_tax = self._create_product(
            name="DP rounding fixed tax",
            type="consu",
            invoice_policy="order",
            taxes_id=self.tax_sale_a + fixed_tax,
        )
        order = self._create_order([(self.product_a_tax, 0.5, 1.01), (product_with_fixed_tax, 0.5, 1.01)])
        downpayment, final_invoice = self._invoice_downpayment_and_balance(order, 50)

        self.assertAlmostEqual(
            downpayment.amount_untaxed + final_invoice.amount_untaxed,
            order.amount_untaxed,
            places=2,
            msg="la base facturada no puede diferir de la base de la orden",
        )

    def test_full_downpayment_consolidated_billing(self):
        """Una sola factura final que deduce un anticipo por cada orden.

        El wizard redondeo cada anticipo contra su propia orden, asi que la particion tiene que
        incluir la orden: si se agregaran todas las lineas juntas, la deduccion no cancelaria.
        """
        orders = self.env["sale.order"]
        for dummy in range(2):
            order = self._create_order([(self.product_a_tax, 0.5, 1.01)])
            order.action_confirm()
            self.env["sale.advance.payment.inv"].with_context(
                active_model="sale.order", active_ids=order.ids, active_id=order.id
            ).create({"advance_payment_method": "percentage", "amount": 100}).create_invoices()
            order.invoice_ids.action_post()
            orders |= order

        final_invoice = orders._create_invoices(final=True)

        self.assertEqual(len(final_invoice), 1, "las ordenes del mismo cliente se agrupan en una factura")
        self.assertEqual(len(final_invoice.invoice_line_ids.filtered("is_downpayment")), 2)
        self._assert_no_spurious_refund(final_invoice)
        self.assertAlmostEqual(final_invoice.amount_total, 0.0, places=2)

    def test_full_downpayment_in_two_rounds_with_discount(self):
        """Residuo por descuento y anticipo cobrado en dos tandas sobre la misma orden.

        Es la forma en que aparece en la practica: el subtotal crudo no cae en medio centavo por una
        cantidad decimal sino por un descuento (597895.50 con 15% => 508211.175), y la orden puede
        arrastrar mas de una linea de anticipo del mismo grupo porque se anticipo dos veces. El
        objetivo del grupo sigue siendo su agregado redondeado una sola vez.

        Con estos importes las dos tandas suman exactamente el agregado redondeado del grupo, asi
        que la factura final cierra en cero. Cuando no lo hacen, el wizard cobra de mas y la final
        sale negativa por ese centavo; eso es previo a este ajuste y lo cubre
        test_downpayment_rounded_up_in_several_rounds. Lo que se verifica en los dos casos es la
        invariante: lo facturado no puede diferir del total de la orden.
        """
        order = self._create_order([(self.product_a_tax, 1.0, 597895.50), (self.product_a_tax, 1.0, 3210000.0)])
        order.order_line.discount = 15.0
        order.action_confirm()
        for dummy in range(2):
            self.env["sale.advance.payment.inv"].with_context(
                active_model="sale.order", active_ids=order.ids, active_id=order.id
            ).create({"advance_payment_method": "percentage", "amount": 50}).create_invoices()
        downpayments = order.invoice_ids
        downpayments.action_post()
        self.assertEqual(len(downpayments.invoice_line_ids.filtered("is_downpayment")), 2)

        final_invoice = order._create_invoices(final=True)

        self._assert_no_spurious_refund(final_invoice)
        self.assertAlmostEqual(final_invoice.amount_total, 0.0, places=2)
        self.assertAlmostEqual(
            sum(downpayments.mapped("amount_total")) + final_invoice.amount_total,
            order.amount_total,
            places=2,
        )

    def test_full_downpayment_with_downpayment_account_configured(self):
        """Cuenta de anticipo propia en la categoria del producto.

        Asi esta configurado en la practica: la linea de anticipo termina en una cuenta distinta a la
        de ingresos de la linea de producto que dedujo. La particion no puede depender de re-derivar
        esa cuenta desde el producto.
        """
        downpayment_account = self.env["account.account"].create(
            {"name": "Anticipos de clientes", "code": "ANT001", "account_type": "liability_current"}
        )
        self.product_a_tax.categ_id.property_account_downpayment_categ_id = downpayment_account
        order = self._create_order([(self.product_a_tax, 0.5, 1.01)])
        downpayment, final_invoice = self._invoice_downpayment_and_balance(order, 100)

        self.assertEqual(
            downpayment.invoice_line_ids.filtered("is_downpayment").account_id,
            downpayment_account,
            "el anticipo tiene que haber ido a la cuenta configurada en la categoria",
        )
        self._assert_no_spurious_refund(final_invoice)
        self.assertAlmostEqual(final_invoice.amount_total, 0.0, places=2)

    def test_downpayment_rounded_up_in_several_rounds(self):
        """El wizard puede cobrar de mas al anticipar en tandas, y eso no lo corrige este ajuste.

        Cada tanda redondea su propio importe: dos tandas del 50% sobre 1.01 facturan 0.51 + 0.51 =
        1.02. La factura final sale negativa por el centavo cobrado de mas, con o sin este ajuste
        (aca no hay residuo sub-centavo, asi que el target coincide con el importe crudo y el
        override no cambia nada). Se deja fijado para que se vea que es del wizard y no de este
        arreglo: lo que se sostiene es que lo facturado siga sumando el total de la orden.
        """
        order = self._create_order([(self.product_a_tax, 1.0, 1.01)])
        order.action_confirm()
        for dummy in range(2):
            self.env["sale.advance.payment.inv"].with_context(
                active_model="sale.order", active_ids=order.ids, active_id=order.id
            ).create({"advance_payment_method": "percentage", "amount": 50}).create_invoices()
        downpayments = order.invoice_ids
        downpayments.action_post()

        final_invoice = order._create_invoices(final=True)

        # el ajuste no toca estas lineas: sin residuo sub-centavo el objetivo es el importe crudo
        targets = final_invoice.downpayment_base_targets or {}
        for line in final_invoice.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and not line.is_downpayment
        ):
            self.assertAlmostEqual(abs(targets.get(str(line.id), 0.0)), abs(line.price_subtotal), places=2)
        self.assertGreater(
            sum(downpayments.mapped("amount_untaxed")),
            order.amount_untaxed,
            "el escenario requiere que el wizard haya cobrado de mas",
        )
        sign = 1 if final_invoice.move_type == "out_invoice" else -1
        self.assertAlmostEqual(
            sum(downpayments.mapped("amount_untaxed")) + sign * final_invoice.amount_untaxed,
            order.amount_untaxed,
            places=2,
            msg="lo facturado tiene que seguir sumando la base de la orden",
        )

    def test_purchase_bill_is_not_adjusted(self):
        """El ajuste es solo de ventas.

        purchase tambien setea is_downpayment en account.move.line, y en un documento de compra la
        clave de grupo no aplica (no hay sale_line_ids, asi que lineas de distintas ordenes de compra
        caerian en un mismo grupo). Ademas la contabilidad de compras no es asunto de este modulo.
        """
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a_tax.id,
                            "quantity": 0.5,
                            "price_unit": 1.01,
                            "tax_ids": [Command.clear()],
                        }
                    )
                    for dummy in range(3)
                ]
                + [
                    Command.create(
                        {
                            "product_id": self.product_a_tax.id,
                            "quantity": -1.0,
                            "price_unit": 1.52,
                            "tax_ids": [Command.clear()],
                            "is_downpayment": True,
                        }
                    )
                ],
            }
        )

        self.assertFalse(bill.downpayment_base_targets, "una factura de compra no tiene que recibir el ajuste")
