.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=======
Sale UX
=======

Several Improvements to sales:

#. Make sale quotations menu not visible.
#. Hide sale invoicing menu (you can already filter on sales orders menu)
#. Add filters in the sale order view
#. Make sale orders menu show all sale records (quotations, and confirmed ones). Make that, by default, links to sale orders shows "sale" data and not only "quotation" data.
#. Add option in settings to show "Customer Reference" field on Sale Order tree view and in the main section of the form view.
#. Add a menu item on Orders for "Sale Order Lines" and improve views with more fields.
#. Allow cancel sales orders in locked state and unlock it after cancelling
#. Fix in button "Create invoice" in sale orders, to create a refund invoice if the sale order amount it's zero and the line's quantities are negative (because of a return).
#. Block cancellation of a sale order if there is a related invoice in a state different from "draft" or "cancel".
#. Customer Preview" button in sale orders, opens the online quotation in a new tab.
#. We rename the field price_subtotal and price_total to "Subtotal" and "Total" respectively in sale.order.form
#. Add option in Sales settings to update prices automatically.
#. Add selection field to force "Invoiced" status of a sale order, available only for admin with tec features.
#. Add options in settings to allow any user as salesman (portal or internal)
#. Add a setting to create an analytic account without company when confirming the sale (requires enabling analytics accounting)
#. Add tracking to payment terms on sale orders.
#. Add the field "Internal Notes" in the sales order form and the setting to allow propagating the "Internal Notes / terms & conditions" to invoices / pickings.
#. Automatically refresh taxes when changing fiscal position
#. Do not use fiscal positions on prices. By default, when using fiscal position and taxes included on the price on sale orders, the price used on the sale line will be the price without the tax being replaced. We added the possibility to take that functionality, or not, with the setting "deduct price-included taxes" in fiscal positions. There are some issues where this is already discussed in odoo standard. For eg. https://github.com/odoo/odoo/issues/66875
#. Makes the "update prices" button visible.
#. Show product image on report
#. Add a setting for automatic cancellation of quotations

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Nothing to configure

Usage
=====

To use this module, you need to:

#. To view Sale Orders Lines, go to: Sales/Sales/Sale Lines

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
