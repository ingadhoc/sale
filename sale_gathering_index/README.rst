.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

====================
Sale Gathering Index
====================

#. Indexes a gathering order: it measures how much the list prices of the gathered products moved since the order was confirmed, and prices what the customer redeems with that index.

#. The index is the weighted price variation of the gathered products, and the coefficient is that index plus one. The order also shows the gathering balance, the gathered amount and the withdrawn amount updated by the index.

#. The baseline of each line is the list price stored when the order was confirmed, so a price agreed below the list price does not show up as a price variation.

#. A product redeemed after the confirmation takes its current price divided by the coefficient, and its description carries the current price and the coefficient used.

#. The gathering report prints the index and the coefficient of the order.

#. On a confirmed gathering order, an already gathered product cannot be added twice, the quantity of an added product cannot be raised and the description of a line cannot be changed.

Installation
============

To install this module, you need to:

#. Only need to install the module.

Configuration
=============

To configure this module, you need to:

#. Nothing to configure.

Usage
=====

To use this module, you need to:

#. Confirm the gathering order as usual. The list price of every gathered line is stored as the baseline of the index.

#. As the prices of those products move, the index and the coefficient of the order follow them, weighted by the gathered quantities.

#. Add a line to redeem a product: its price is the current one divided by the coefficient, which is what the customer paid for in advance.

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
