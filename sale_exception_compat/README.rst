.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=====================
Sale Exception Compat
=====================

Keeps the confirmation flow that `sale_exception` had before
OCA/server-tools#3590: the exceptions are detected before any other module
overrides `action_confirm`, and a sales order that matches a rule rolls back
everything the confirmation did and shows the popup.

The replacement of `detect_exceptions()` itself lives in `base_exception_compat`,
because it is defined on the abstract model every exception module inherits
from and it also covers `stock_exception` and any other one. This module only
keeps what is specific to sales.

Installation
============

To install this module, you need to:

#. Only need to install the module. It is auto installed with `sale_exception`.

Configuration
=============

To configure this module, you need to:

#. Nothing to configure.

Usage
=====

To use this module, you need to:

#. Confirm a sales order that matches an exception rule: the exception popup
   shows up and everything the confirmation did is rolled back.

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
