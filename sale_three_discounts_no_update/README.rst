.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==================================
Sale Three Discounts No Update
==================================

This module restores the previous behavior for three discounts on sale order
lines.
When a line already has manual values in ``discount1``, ``discount2`` or
``discount3``, automatic recomputations keep those values instead of resetting
them.

Installation
============

To install this module, you need to:

#. Just install this module

Configuration
=============

To configure this module, you need to:

#. No configuration needed

Usage
=====

To use this module, you need to:

#. Set manual values in three discounts fields on sale order lines.
#. Update product, quantity or prices and keep manual discounts unchanged.

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

* Carolina Dziubek

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
