.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===========================================
Sale Require Purchase Order Number - Chile
===========================================

In Chile the customer purchase order travels to SII as an ODC cross reference
(``l10n_cl.edi.reference``) of the delivery guide and of the invoice, and is printed
on both PDFs in the references table. ``l10n_cl_edi_stock`` builds that reference
from "Your Reference" (``client_order_ref``) and only on delivery guides. With this
module:

* The delivery guide reference takes the "Purchase Order Number" of the sale order,
  also when "Your Reference" is empty and on deliveries in two or three steps. A
  reference the user edits on a previous picking is kept on the next one.
* Customer invoices created from sale orders get one ODC reference per sale order
  with a purchase order number.

Installation
============

To install this module, you need to:

#. Nothing: it is installed on its own when ``sale_require_purchase_order_number``
   and ``l10n_cl_edi_stock`` are both installed.

Configuration
=============

To configure this module, you need to:

#. A Chilean company with a DTE service provider set.

Usage
=====

To use this module, you need to:

#. Set the "Purchase Order Number" on a sale order and confirm it.
#. The delivery guide and the invoice carry the purchase order reference.

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
