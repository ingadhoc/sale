.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

======================================
Stock availability in sales order line
======================================

* Add two groups. One for seeing stock on sale orders and other to see only if or not available.
* Add an option in warehouse to disable stock warning

IMPORTANT:
----------
* This module could break some warnings as the ones implemented by 'warning' module
* If you dont disable warning and give a user availbility to see only 'true/false' on sale order stock, he can see stock if the warning is raised


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

#. If you want to add a product to the sales order line, the warning appears, if the stock of this product is less than the amount set.

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
