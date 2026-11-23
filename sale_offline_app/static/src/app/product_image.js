import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/** Product thumbnail fetched online with the API key; offline it shows a placeholder. */
export class ProductImage extends Component {
    static template = "sale_offline_app.ProductImage";
    static props = { product: Object };

    setup() {
        this.preventa = useService("preventa");
        this.data = useState(this.preventa.state);
        this.state = useState({ url: null });
        onWillStart(() => this.load(this.props.product));
        onWillUpdateProps((nextProps) => this.load(nextProps.product));
    }

    load(product) {
        this.state.url = null;
        if (!product.has_image || !this.data.online || !this.data.link) {
            return;
        }
        // Not awaited: the row renders right away and the image shows up when it arrives.
        this.preventa.getImageUrl(product.id).then((url) => {
            if (product.id === this.props.product.id) {
                this.state.url = url;
            }
        });
    }
}
