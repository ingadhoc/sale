.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

================================
Sale Order Type Invoicing Policy
================================

Add to sale order type invoice policy field with possible values:

#. Defined by Product: default odoo behaviour, invoice qty will be computed considering product configuration.
#. Prepaid- Block Reserve and Delivery: They cannot reserve or deliver products until the invoice for the total has been created and is fully paid.
#. Prepaid- Block Delivery: They cannot deliver products until the invoice for the total has been created and is fully paid.
#. Ordered quantities: overwrites product behaviour so that all lines are considered as "ordered quantities" no matter product configuration, once order is confirmed all products should be invoiced.
#. Delivered quantities: overwrites product behaviour so that all lines are invoiced on the delivered quantity, no matter product configuration.
#. Returns are taken into account: for the prepaid and "Ordered quantities" policies, the quantity returned (field added by sale_stock_ux) is subtracted from the quantity to invoice, so a return can be refunded.

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

#. Go to Sales / Configuration / Sale Order Types and set the "Invoicing Policy" of the type.
#. Create a sale order with that type: the quantity to invoice of every line follows the policy of the type instead of the one of the product.
#. With a prepaid policy, the "Check Availability" and "Force Availability" buttons of the delivery raise an error until the order is fully invoiced and paid.

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
