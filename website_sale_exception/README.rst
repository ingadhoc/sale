.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

======================
Website Sale Exception
======================

<<<<<<< a322fed2eb1c0a1f2d9d09d2a859e077dbe514a4:website_sale_exception/README.rst
This module integrates ``website_sale`` with ``sale_exception_print`` to prevent errors
when previewing sale orders with print exceptions.
||||||| 4c7ce07806366e210dd9527d651eb4175bc3f763:sale_exception_compat/README.rst
Keeps the exception flow that `sale_exception` had before OCA/server-tools#3590,
where `detect_exceptions()` writes in the ongoing transaction and returns the
rules instead of writing through a second cursor and raising.

The upstream mechanism opens a second database connection to store the
exceptions. That connection writes the same rows the ongoing transaction is
about to write, so the confirmation either fails with a serialization error or
blocks until the worker is killed. It also turns the exception into an error
for any caller outside the backend web client (portal, e-commerce, API, cron),
because the handler that translates it into a popup is only registered in
`web.assets_backend`.
=======
Keeps the confirmation flow that `sale_exception` had before
OCA/server-tools#3590: the exceptions are detected before any other module
overrides `action_confirm`, and a sales order that matches a rule rolls back
everything the confirmation did and shows the popup.

The replacement of `detect_exceptions()` itself lives in `base_exception_compat`,
because it is defined on the abstract model every exception module inherits
from and it also covers `stock_exception` and any other one. This module only
keeps what is specific to sales.
>>>>>>> f1b576e6fea7d8aacb1ec6610d37a5b96efa1c10:sale_exception_compat/README.rst

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

#. Just use.

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
