/** @odoo-module **/

import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { patch } from '@web/core/utils/patch';

patch(SaleOrderLineProductField. prototype, {
    /**
     * Override to set first packaging as default UoM when only_packagings is True
     */
    async _openProductConfigurator(edit = false, selectedComboItems = []) {
        const saleOrderLine = this.props.record.data;
        if (saleOrderLine.product_template_id && !edit) {
            const productTemplate = await this.orm.read(
                'product.template',
                [saleOrderLine.product_template_id.id],
                ['only_packagings', 'uom_ids']
            );
            if (productTemplate[0].only_packagings && productTemplate[0].uom_ids.length > 0) {
                await this.props.record.update({
                    product_uom_id: { id: productTemplate[0].uom_ids[0] }
                });
            }
        }
        return super._openProductConfigurator(edit, selectedComboItems);
    },
});
