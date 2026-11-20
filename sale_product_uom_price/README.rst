.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=============================
Sale Price per Product Unit
=============================

Since v19 a packaging is a unit of measure of the line, so a line sold by packaging shows the
price of the packaging as unit price. Customers that buy by weight compare prices per kg, and the
salesperson had to print the quotation to know the price per kg they were selling at.

This module shows that price in the two places it is needed, both on top of the same hook, so
what the salesperson sees and what the customer receives always agree.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Nothing to configure for the column on the order lines.
#. For the printed quotation and the invoices, enable "Show Product Unit on Quotations &
   Invoices" in Sales / Configuration / Settings.

Usage
=====

#. Optional column "Price per Product Unit" on the sale order lines: the unit price in the unit of
   the product (e.g. per kg on a line sold by packaging of 20 kg), with the same tax criteria as
   the printed quotation. It is hidden by default, is added from the optional columns selector,
   and does not depend on the setting below.
#. The column is editable in both directions: changing it recomputes the unit price of the line,
   and changing the unit price recomputes it. The line keeps the price as a manual one, so
   changing the quantity does not bring back the price of the pricelist.
#. With the setting enabled, the quotation PDF and the online quotation show those lines in the
   unit of the product: quantity and unit price in kg, with the line unit as a secondary detail.
#. With the setting enabled that price is also the one that rules: it is rounded to the decimals
   of "Product Price" and the unit price of the line follows it, so the quantity and the price of
   the printed document multiply into the subtotal of the line. A price list that rounds its
   prices rounds the price of the packaging, and the division to the product unit used to bring
   the extra decimals back.
#. With the setting enabled those lines are also invoiced in the unit of the product: the invoice
   line carries the quantity and the price per product unit, so the invoice states the same price
   the quotation printed and both documents add up to the same amounts. The order goes on counting
   what it has invoiced in its own unit.
#. Without the setting the unit price of the line rules, and the price per product unit carries
   four decimals so that quantity x unit price still matches the subtotal.

For a localization that prints the price with taxes, implement
``_get_report_price_unit()`` on ``sale.order.line``: the inverse used when the column is edited is
derived from it, so there is nothing else to write.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/ingadhoc/sale/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Credits
=======

Authors
~~~~~~~

* ADHOC SA

Maintainer
~~~~~~~~~~

|company_logo|

This module is maintained by |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
