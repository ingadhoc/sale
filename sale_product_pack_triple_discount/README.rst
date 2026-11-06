.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=================================
Sale Product Pack Triple Discount
=================================

This module carries the sale discount of a pack component into Discount 1, so it
survives the triple discount.

Without it, ``sale_triple_discount`` recomputes the line discount from Discount 1,
2 and 3 alone, and the discount ``sale_product_pack`` sets on a component line is
lost. It installs itself whenever both modules are present.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Go to Sales settings and enable "Discount per line", which is what shows the
   discount columns on the sale order lines.

Usage
=====

To use this module, you need to:

#. Create a pack product with "Detailed" type and "Detailed" component price, and
   set a sale discount on one of its pack lines.
#. Add the pack to a sale order. The component line shows that discount in
   Discount 1, and Discount 2 and 3 stack on top of it.

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
