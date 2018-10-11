.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

======
POS UX
======

Be able to use POS to generate orders without payment. For this, we add new boolean field to journals named POS Outstanding Payment. Journals used as point of sale payment method that has this boolean will not generate payments or create account.move.line to reconcile.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Configure the journal you want to use for Outstanding payment by activate the
related boolean in the journal form.

  >> *IMPORTANT:* We highly recommend that of you are going to use a payment method as POS Outstanding payment please do not select any inboud / outbound methods in order to not show this payment method in conventional receipts and payments.

#. Ensure that the journal is added as payment method of your point of sale, this can be checked in Point of Sale / Configuration / Point of Sale / Payments.

Usage
=====

To use this module, you need to:

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
