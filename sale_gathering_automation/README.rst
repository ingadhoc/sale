.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================
Sale Gathering Automation
=========================

#. Bridge module between sale_gathering and sale_order_type_automation so that the invoice is created in 0 discounting the gathering from the automation.

#. On a gathering order, confirming it creates the gathering invoice for the gathered amount, and validates it unless the sale type's draft invoice domain matches.

#. The Create Invoice button runs the invoicing automation instead of opening the down payment wizard, and opens the resulting invoice.

#. Changing a quantity on a gathering order runs the picking automation of its sale type. The invoicing automation is not run on save, because on gathering it is too invasive.

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

#. Set the sale type of the gathering order with an invoicing automation, a picking automation, or both.

#. Confirm the order and pay its gathering invoice. From then on, every withdrawal runs the automations of the sale type.

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
