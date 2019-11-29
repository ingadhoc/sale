.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================
Sale Order Validity
===================

* This module allows to set how many days valid is the quotation.
* By default the number of days of validity is chosen from the company.
* It is posible to modify the numbers of days only if the new number is lower than the one set in the company.
* The validation date is calculated as the date the quotation was created + days validity.
* If the validaty date is in the past it is not posible to validate the quotation.
* A new button is created to reset the validity date and reset the prices of every line.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:
#. Go to Settings / General Settings.
#. Select Sales Menu.
#. In Quotations & Orders section you'll see Sale Order Validity Days field.

Usage
=====

To use this module, you need to:

#. You can established the quantity of days to validty the sale order.

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
