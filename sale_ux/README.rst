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

#. Make subtotal included / excluded optional and not related to tax b2b/b2c
#. Hide sale invoicing menu (you can already filter on sales orders menu)
#. Make button send by email also available on done state on sale orders.
#. Make sale quotations menu only visible with technical features.
#. Make sale orders menu show all sale records (quotations, and confirmed ones).
#. Add a menu item on sales for 'sale lines' and improve views with more fields.
#. Make that, by default, links to sale orders shows "sale" data and not only "quoatation" data.
#. Make cancel button also visible on done state so that if "Never allow to modify a confirmed sale order" is enable, sale users can still cancel a sale order that has not been delivered or invoiced yet.
#. Add button to force "invoiced" only for admin with tec features.
#. Add tracking to payment term and pricelist on sale orders.
#. Add option to show SO reference field on tree view and on main section of form view.
#. Add filter to be able to select analytic account on sale orders with the same partner/commercial partner as the sale order.
#. Add Commercial Partner is automatic set in the sale order taking into account the partner configuration
#. It adds a button in sale quotations that allowes to update sale prices. It is useful if the pricelist is changed after adding sale order lines. (Only Update the prices if the product has price defined or different than zero).
#. Add a wizard on sales orders that allow you to define global discounts to sale orders by percentage.
#. Add a link from invoices to the sale orders that generate it.
#. Add option in setting to update prices automatically.
#. Fix the filter Sales in Sale orders to filter in states "sale" and "done".
#. Add column "date_order" in sale order tree view.
#. Fix in button "create invoice" in sale order, to create an refund invoice if the amount it's cero and the lines quantities are negative.
#. Add to sale order lines action the form view, to access with the button "sales" in product template.
#. Preview button in Sale Order now open the online quotation in a new Tab

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
