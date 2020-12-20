.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=============
Sale Stock UX
=============

Several Improvements to sales:

#. Add delivery status on sales
#. Block cancelation of sale order if there are pickings in 'done' state or 'posted' invoices (this is native on purchase orders)
#. Add button on sale lines to allow cancelling of remaining qty to be delivered
#. Block decreasing qty on sale lines when there is a delivery linked
#. Add procurement group field on sale orders for technical features
#. Add a filter name "Pickings" in sale order to filter by voucher name.
#. Add new field on order lines "quantity_returned" and also implement refunds for products with invoicing type "ordered"
#. Add filter for sale orders with returns
#. Integrate delivery status with returns logic
#. Propagate observations and notes from SO to pickings and invoices
#. Add moves on sale order line form view (only for technical features)
#. Add an option in warehouse to disable stock warning

IMPORTANT:
----------
* This module could break some warnings as the ones implemented by 'warning' module
* If you dont disable warning and give a user availbility to see only 'true/false' on sale order stock, he can see stock if the warning is raised

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

#. If you want to add a product to the sales order line, the warning appears, if the stock of this product is less than the amount set.

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
