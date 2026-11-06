##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.tests.common import TransactionCase


class ProductUomPriceCommon(TransactionCase):
    """A customer, a product sold by weight and two packagings of it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Its own company, so a localization installed in the base (taxes required per line,
        # for instance) does not decide whether these tests can create a line
        cls.company = cls.env["res.company"].create({"name": "Product UoM Price Co"})
        cls.env.user.company_ids = [Command.link(cls.company.id)]
        cls.env = cls.env(
            context={
                **cls.env.context,
                **DISABLED_MAIL_CONTEXT,
                "tracking_disable": True,
                "allowed_company_ids": [cls.company.id],
            }
        )
        cls.env.user.company_id = cls.company
        cls.pricelist = cls.env["product.pricelist"].create(
            {"name": "Product UoM Price List", "company_id": cls.company.id}
        )
        cls.IrConfig = cls.env["ir.config_parameter"].sudo()
        cls.setting = "sale_product_uom_price.report_in_product_uom"

        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_box_20 = cls.env["uom.uom"].create(
            {"name": "Box 20 kg", "relative_factor": 20.0, "relative_uom_id": cls.uom_kg.id}
        )
        cls.uom_box_15 = cls.env["uom.uom"].create(
            {"name": "Box 15 kg", "relative_factor": 15.0, "relative_uom_id": cls.uom_kg.id}
        )
        cls.product_kg = cls.env["product.product"].create(
            {
                "name": "Welding wire",
                "type": "consu",
                "list_price": 7.27,
                "uom_id": cls.uom_kg.id,
                "uom_ids": [Command.set([cls.uom_box_20.id, cls.uom_box_15.id])],
                "taxes_id": [Command.clear()],
            }
        )
        # An explicit language, activated here in case the base only has another one installed:
        # the report renders with the language of the customer, and without a known one the
        # decimal separator of the base decides whether a price reads 7.27 or 7,27
        cls.env["res.lang"]._activate_lang("en_US")
        cls.partner = cls.env["res.partner"].create({"name": "Product UoM Price Customer", "lang": "en_US"})

    @classmethod
    def _create_order(cls, uom, qty, price_unit, discount=0.0):
        return cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "company_id": cls.company.id,
                "pricelist_id": cls.pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product_kg.id,
                            "product_uom_id": uom.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                            "discount": discount,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
