.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

============================
Sale Product Pack Product UX
============================

On the product catalog opened from a sale order, this module shows the price of the whole pack (the pack product plus its components) for a pack displayed as detailed and with detailed component prices. Without it, only the price of the pack product is shown.

It covers the three places where that price is read:

#. The unit price of the catalog kanban and the ``product_catalog_price`` field of ``product_catalog_tree`` ("Order Price" column), through ``sale.order._get_product_catalog_order_data``.
#. The ``pricelist_price`` field of ``product_ux`` ("Pricelist Price" column), through ``_compute_product_pricelist_price``. The price is computed with the pricelist and the date of the order, so it is shown in the currency of the order.
#. The pack already on the order, through ``sale.order.line._get_product_catalog_lines_data``, which adds the share of the component lines with their discounts.
#. The price the catalog shows right after adding or removing the pack with the quantity buttons, through ``sale.order._update_order_line_info``.

Installation
============

To install this module, you need to:

#. Just install.

Configuration
=============

To configure this module, you need to:

#. Nothing to configure.

Usage
=====

To use this module, you need to:

#. Set a product as a pack with "Pack Type" detailed and "Pack Component Price" detailed per component.
#. Open a quotation and go to the product catalog: the unit price of the pack and the pricelist price column show the price of the pack with its components.
#. Add the pack to the quotation: the catalog keeps showing the price of the whole pack, now with the prices and discounts of the order lines.

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
