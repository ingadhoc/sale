/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const websiteSaleAddress = publicWidget.registry.websiteSaleAddress;


websiteSaleAddress.include({

    // @override
    _onSaveAddress: async function (ev) {
            if (!this.addressForm.reportValidity()) {
            return
        }

        const submitButton = ev.currentTarget;
        if (!ev.defaultPrevented && !submitButton.disabled) {
            ev.preventDefault();
            if(ev.currentTarget.closest('form').action.includes('portal/address') ){
                submitButton.disabled = true;
                const spinner = document.createElement('span');
                spinner.classList.add('fa', 'fa-cog', 'fa-spin');
                submitButton.appendChild(spinner);

                const result = await this.http.post(
                    '/portal/address/submit',
                    new FormData(this.addressForm),
                )
                if (result.successUrl) {
                    window.location = '/portal/addresses';
                } else {
                    // Highlight missing/invalid form values
                    document.querySelectorAll('.is-invalid').forEach(element => {
                        if (!result.invalid_fields.includes(element.name)) {
                            element.classList.remove('is-invalid');
                        }
                    })
                    result.invalid_fields.forEach(
                        fieldName => this.addressForm[fieldName].classList.add('is-invalid')
                    );

                    // Display the error messages
                    // NOTE: setCustomValidity is not used as we would have to reset the error msg on
                    // input update, which is not worth catching for the rare cases where the
                    // server-side validation will catch validation issues (now that required inputs
                    // are also handled client-side)
                    const newErrors = result.messages.map(message => {
                        const errorHeader = document.createElement('h5');
                        errorHeader.classList.add('text-danger');
                        errorHeader.appendChild(document.createTextNode(message));
                        return errorHeader;
                    });

                    this.errorsDiv.replaceChildren(...newErrors);

                    // Re-enable button and remove spinner
                    submitButton.disabled = false;
                    spinner.remove();
                }
            } else {
                this._super(...arguments);
            }
        }
    }
})
