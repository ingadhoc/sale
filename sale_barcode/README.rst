.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

============
Sale Barcode
============

Add the posibility to manage sale orders with barcode interface.
Only need to create the sale order, set the partner and then start to scanning the products.
You can use also the barcoders in order to save / edit / print / confirm order / cancel a sale order.

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

Packagings
----------

A packaging is a unit of measure of the product, listed on its *Sales* tab
under *Packagings*, and its barcode is set on that unit of measure (*Packaging
Barcodes*). Both barcodes are taken into account when scanning on a sale order:

* Scanning the product barcode adds one unit.
* Scanning a packaging barcode adds one packaging, on a line expressed in that
  packaging unit.

The quantity of an existing line is always expressed in the unit of that line,
so scanning a packaging on a line sold by unit adds its whole content.

Known limitations
=================

Scanning a unit on a line sold by packaging adds a whole packaging
------------------------------------------------------------------

Scanning a packaging of 6 units and then scanning the same product by unit
leaves the line at 2 packagings, that is 12 units, instead of the 7 units that
were actually scanned. The line already exists in the packaging unit, and the
scan is added in that unit.

Adding the exact amount instead would put a fraction of a packaging on the
line, and a decimal quantity where the salesperson counted whole items. So
selling a packaging plus some loose units of the same product needs the loose
units to be set by hand on their own line.

We decided to keep the current behaviour for now, rather than add the
complexity of splitting a line per unit of measure, because we do not expect
this to be a common case.

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
