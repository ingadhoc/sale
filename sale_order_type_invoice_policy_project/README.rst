.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |company_icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

========================================
Sale Order Type Invoicing Policy Project
========================================

Bridge between "Sale Order Type Invoicing Policy" and "sale_project".

Adds the "Exclude prepaid services" option to the sale order type. When the type
uses the "Delivered quantities" invoicing policy and this option is on, service
products with an "ordered_prepaid" service policy are invoiced by ordered
quantity instead of delivered quantity.

The option lives here because ``service_policy`` is defined by ``sale_project``:
without that module the field does not exist and the invoicing policy cannot
take it into account.

Installation
============

To install this module, you need to:

#. Only need to install the module. It is installed automatically when both
   "Sale Order Type Invoicing Policy" and "sale_project" are present.

Configuration
=============

To configure this module, you need to:

#. Go to the sale order type, set the invoicing policy to "Delivered
   quantities" and check "Exclude prepaid services"

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

* |company| |company_icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
