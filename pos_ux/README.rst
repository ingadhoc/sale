.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

================
Point of Sale UX
================

1. Setting "Billing behavior" with billing options:

   a. **Invoice on demand**: the user can check to invoice.

   b. **By default invoice**: invoice is issued by default.
      It is allowed to change to not invoice

   c. **Always Invoice**: invoice is always issued

2. **Block invoiced download**: setting that cancels the download of the PDF invoice

3. **Adds the contingency mode** for when connection fails

4. Makes the "receivable account" of payment methods mandatory

5. If a payment method does not have a "receivable account" and "outstanding account" defined, it will not allow you to log in to the POS.

6. **Payment methods are created with "Identify Customer" enabled by default** (``split_transactions = True``).

7. **Default customer**: setting that pre-selects a partner on every new POS order.
   Useful for B2C points of sale where most sales go to a generic anonymous customer.

8. **Block session close when there are paid orders without invoice**. Only
   applies when the billing behavior is set to "Always Invoice". Use the
   "Generate invoices" button in the session backend to invoice the pending
   orders before closing the session.

9. **Invoiced / Not Invoiced pill in the orders list**. Paid orders show a
   badge in the ticket screen indicating whether they were already invoiced,
   so the cashier can tell at a glance which orders are still pending.


Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#.

Usage
=====

To use this module, you need to:

#.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

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

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
