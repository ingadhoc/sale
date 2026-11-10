.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

========================
Sale Gathering Delivery
========================

Excludes delivery lines from gathering calculations (balance, amount, index and coefficient).

A delivery line is charged, not gathered:

* On a gathering order, delivery lines are left out of the gathered lines. When the
  order is confirmed they keep their quantity instead of moving it to the initial
  gathered quantity, and their amount stays out of the gathered amount and of the
  balance.
* The gathering down payment invoice (fixed amount) also carries the delivery lines,
  so the customer pays the freight together with the gathering instead of getting a
  separate invoice for it.
* An invoice whose only lines are the down payment and the delivery lines of a
  gathering order still counts as a down payment invoice.

Auto-installs when both sale_gathering and delivery are installed.

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

* ADHOC SA: `Icon <https://github.com/ingadhoc/maintainer-tools/blob/master/resources/adhoc-icon.png>`_.

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by ADHOC SA.

To contribute to this module, please visit https://www.adhoc.com.ar.
