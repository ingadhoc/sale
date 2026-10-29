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

#. Shows delivery status in the sale tree view.
#. Computes the native "To Deliver" filter (and its dashboard card) with the delivery status of the lines, which discounts returns and respects the forced delivery status. Adds "Fully Delivered" and "With Returns" filters on sale orders, and "To Deliver" and "Fully Delivered" filters on sales order lines.
#. Add field "qty_to_deliver" in the sale lines view.
#. Add new field on order lines called "quantity_returned" and also implement refunds for products with invoicing policy "ordered" taking into account the returned quantity.
#. Block cancelation of sale order if there are pickings in 'done' state.
#. Add button on sale lines to allow cancelling of remaining qty to be delivered, and an action to cancel the remaining quantities of several sale orders at once.
#. Block decreasing quantity on sale lines when there is a delivery linked.
#. Integrate delivery status with returns logic.
#. Propagate Internal Notes from SO to pickings.
#. Add selection field to force "Delivery" status of a sale order, available only for admin with tecH features.
#. Add parameter in settings to propagate the UoM from the sale order to the picking.
#. Add the information of the stock available by location in the forecast widget at the sale order line.
#. Add a "Sale Order" smart button on stock moves linked to a sale order.

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
