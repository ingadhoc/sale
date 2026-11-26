.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=================
Sale Exception UX
=================

* Hides the exception field from the sale order list view by making it optional="hide"
* Restricts the ability to ignore exceptions to only sales managers
* Turns the "Ignore Exceptions" button of the alert into "Ignore and Confirm":
  it checks every rule again and, when none of the failing ones is blocking,
  ignores them and confirms the order in the same step

  Ignoring used to only set the flag, and a flagged order was left out of every
  later detection: a rule that turned blocking afterwards was never evaluated
  again and the order confirmed without any warning.

Installation
============

To install this module, you need to:

#. Only need to install the module.

Configuration
=============

To configure this module, you need to:

#. Nothing to configure

Usage
=====

To use this module:

#. The exception field in the sale order list view will be hidden by default.
#. Only users with sales manager or exception rule manager permissions can ignore exceptions.
#. "Ignore and Confirm" re-checks the rules: if a blocking one fails, the order
   is neither ignored nor confirmed and the blocking exceptions are listed;
   otherwise the order is ignored and confirmed at once. A confirmed order is
   only ignored.
#. On upgrade, the flag is cleared from the quotations that carry it and were
   never confirmed, so they stop skipping the blocking rules.

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
