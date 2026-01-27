import base64
import io

from odoo import api, fields, models
from PIL import Image, WebPImagePlugin  # Importación explícita del plugin


class ProductTemplate(models.Model):
    _inherit = "product.template"

    image_sale_order = fields.Binary(
        "Report Image",
        compute="_compute_image_sale_order",
        store=True,
    )

    @api.model
    def action_recompute_image_sale_order(self):
        self._compute_image_sale_order()

    @api.depends("image_128")
    def _compute_image_sale_order(self):
        if not self.env["ir.config_parameter"].sudo().get_param("sale_ux.show_product_image_on_report"):
            self.image_sale_order = False
            return

        with_image = self.filtered("image_128")
        for template in with_image:
            # Decodificar la imagen base64
            image_data = base64.b64decode(template.image_128)
            # Si no es WebP, mantener la imagen original
            if not image_data.startswith(b"RIFF") and b"WEBP" not in image_data[:12]:
                template.image_sale_order = template.image_128
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
