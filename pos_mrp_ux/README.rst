.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

====================
Point of Sale MRP UX
====================

Keeps a kit from being over delivered when one of its components is also sold loose in the same PoS order.

On Odoo 19, when a kit and a lot tracked component of that kit are on the same order, the lots the cashier picked for the loose lines are also written on the move that the kit explosion created. That move gets its whole demand once per line and per lot, so it ends up over its demand: the delivery takes more stock than it sold, and on a picking type with ``Block additional quantity`` the order fails to sync with ``You can not transfer more than the initial demand!``. This module assigns the exploded move the same way as when the kit is sold on its own.

This is a bridge, not a feature: the defect is Odoo's own and shows up on a database with no Adhoc or OCA module installed, both with the ``pos_mrp`` of the 19.0 branch and with the one of master. Odoo tracks it as issue n.4 of `odoo/odoo#279822 <https://github.com/odoo/odoo/pull/279822>`_, open as a draft with conflicts since 2026-07-31. Once that lands, this module goes away.

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

#. Nothing special, it works automatically when selling a kit from the PoS

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
