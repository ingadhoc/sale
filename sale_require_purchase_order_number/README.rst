.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==================================
Sale Require Purchase Order Number
==================================

This module incorporates the following features:

* Field "purchase order number" on sale order, picking and invoice.
* Validate that the field is in these documents if the partner has the field "required number of PO".
* Purchase order number must be unique per partner

Regional scope
==============

This module only stores and validates the field. Printing it on a document, or
sending it to a tax authority, is done by each localization, so what you get out
of the box depends on the country:

* **Argentina** (``l10n_ar_ux``, ``l10n_ar_stock_ux``): printed as "PO Number" on
  the invoice and on the delivery slip PDF.
* **Uruguay** (``l10n_uy_ux``): sent to DGI in the ``CompraID`` tag of the CFE,
  replacing the value taken from ``ref``.
* **Chile** (``l10n_cl_edi``, ``l10n_cl_edi_stock``): sent to SII as an ODC cross
  reference of the invoice and of the delivery guide, and printed on both PDFs in
  the references table. Without this module that cross reference is built from
  "Your Reference" (``client_order_ref``) instead.
* **Any other country**: the field is only stored on the record, it is not printed
  on any document.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Set in the partner the boolean to require the "Purchase Order Number".

Usage
=====

To use this module, you need to:

#. Create an sale order with a partner with required the "Purchase Order Number" and set it.
#. Then validate and create an invoice.

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
