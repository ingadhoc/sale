.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=====================
Sale Payment Options
=====================

Allows defining and displaying multiple payment options on quotations and sales orders.

- Configure several payment options per sales order.
- Edit payment options only through a wizard.
- Reusable payment option templates.
- Visual display of payment options in the order.
- Automatic recalculation if the order total changes.
- Each payment option can have multiple installment plans.
- Payment options are shown in the sales order PDF, with tables, subtotals, and totals.
- Handles missing or malformed data gracefully in reports.
- Optionally, print the installment amounts per sale order line instead of the order-wide table.

Installation
============

To install this module, you need to:

#. Just install.

Configuration
=============

To print the installment amounts discriminated by line, you need to:

#. Go to *Sales > Configuration > Settings > Quotations & Orders*.
#. Enable *Payment Options Display: Discriminate by sale order line*.

With that option enabled the printed quotation shows, under each line, the amount per
installment of every payment option (e.g. *3 installments of $ 41,600.00 | 6 installments
of $ 24,000.00*), the order-wide payment options table is not printed and the standard
totals summary is shown instead. The setting is per company.

The installment amounts are always computed on the line amount with taxes included, no
matter whether the report prints the line amounts with or without taxes.

Usage
=====

#. Open a sales order and go to the "Payment Options" tab.
#. Click "Edit Payment Options" to use the wizard.
#. Select a template or add payment lines manually.
#. Save to apply the payment options to the order.
#. The summary appears in the order (read-only).
#. When printing, payment options are shown as tables with installment details and totals.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/sale/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

* ADHOC SA <https://www.adhoc.com.ar>

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
