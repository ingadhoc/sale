.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=============================================
Portal Distributor Sale with Order Validity
=============================================

This module integrate portal sale distributor using sale_order_validity.

#. Show the Update Validity button to portal distributor users, next to the
   Update Prices button added by sale_ux inside the order details group, and
   hide it at its native position beside the validity date.
#. Run update_date_prices_and_validity as superuser, since the recomputation
   reaches records the distributor can not write.

Installation
============

To install this module, you need to:

#. Just install this module. It is auto installed when both 'Portal Sale
   Distributor' and 'Sale Order Validity' are installed.

Configuration
=============

To configure this module, you need to:

#. The same as 'Portal Sale Distributor' module.

Usage
=====

To use this module, you need to:

#. Log in with a user with the portal distributor group.
#. Go to Sales and open a quotation in draft or sent state.
#. Press Update Validity in the order details group.

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
