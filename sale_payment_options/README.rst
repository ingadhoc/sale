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
- Payment options are printed from their own report action, with tables, subtotals, and totals.
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
installment of every payment option, prefixed with the name of its installment plan (e.g.
*Cash discount (CASH): 1 installments of $ 41,600.00 | Plan 6 (CARD): 6 installments of
$ 24,000.00*), and the order-wide payment options table is not printed. The setting is per
company.

The installment amounts are always computed on the line amount with taxes included, no
matter whether the report prints the line amounts with or without taxes: they are what
the customer is going to pay.

Printing
========

The module adds a second print action, *Quotation / Order (Payment Options)*, next to the
standard one. The standard action prints the quotation as always, without any payment
option; this one prints it with them.

Both print the same document: the report action only calls the standard wrapper with a flag
in the context, instead of rendering the quotation document itself. That is what keeps the
localizations working, because they register their own version of the document on that
wrapper (in Argentina, the header, the identification block and the *Discriminate Taxes*
setting of the sale order type).

The totals summary of the order is always printed, with the payment options below it.

Usage
=====

#. Open a sales order and go to the "Payment Options" tab.
#. Click "Edit Payment Options" to use the wizard.
#. Select a template or add payment lines manually.
#. Save to apply the payment options to the order.
#. The summary appears in the order (read-only).
#. Print with *Quotation / Order (Payment Options)* to get them on the PDF, as a table
   with installment details and totals, or discriminated by line if the setting above is
   enabled.

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
