import base64
import io

from odoo import _, api, fields, models
from PIL import Image, WebPImagePlugin  # Importación explícita del plugin


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "base.bg"]

    image_sale_order = fields.Binary(
        "Report Image",
        compute="_compute_image_sale_order",
        store=True,
    )

    @api.model
    def action_recompute_image_sale_order(self):
        valid_fields = ["image_128", "image_256", "image_512", "image_1024", "image_1920"]
        image_field = self.env["ir.config_parameter"].sudo().get_param("sale_ux.product_image_field", "image_128")
        if image_field not in valid_fields:
            image_field = "image_128"

        product_ids = self.search([(image_field, "!=", False)])

        if not product_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No products to process"),
                    "type": "warning",
                    "message": _("No products found with images to recompute."),
                },
            }

        # Use bg_enqueue_records to process in batches of 100
        return self.env["base.bg"].bg_enqueue_records(
            product_ids,
            "_compute_image_sale_order",
            threshold=100,
            name=f"Recompute {len(product_ids)} Product Images",
        )[0]

    @api.depends("image_1920")
    def _compute_image_sale_order(self):
        valid_fields = ["image_128", "image_256", "image_512", "image_1024", "image_1920"]
        image_field = self.env["ir.config_parameter"].sudo().get_param("sale_ux.product_image_field", "image_128")
        if image_field not in valid_fields:
            image_field = "image_128"
        with_image = self.filtered(image_field)
        for template in with_image:
            # Decodificar la imagen base64
            image_data = base64.b64decode(template[image_field])
            # Si no es WebP, mantener la imagen original
            if not image_data.startswith(b"RIFF") and b"WEBP" not in image_data[:12]:
                template.image_sale_order = template[image_field]
                continue
            stream = io.BytesIO(image_data)

            # Intentamos abrir forzando el plugin de WebP, preferimos esto
            # porque PIL no siempre detecta correctamente el formato WebP
            try:
                img = WebPImagePlugin.WebPImageFile(io.BytesIO(image_data))
            except Exception:
                # Si falla el plugin directo, intentamos la apertura normal
                stream.seek(0)
                img = Image.open(stream)
            # la imagen tiene canal alfa, convertir a RGB con fondo blanco
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                img = img.convert("RGBA")
                background.paste(img, (0, 0), img)
                img = background
            else:
                img = img.convert("RGB")

            output = io.BytesIO()
            img.save(output, format="JPEG")
            template.image_sale_order = base64.b64encode(output.getvalue())
        (self - with_image).image_sale_order = False

        # Return message for background job notification (only when called from bg job)
        if self.env.context.get("bg_job"):
            return _("Successfully processed %s product images") % len(self)
