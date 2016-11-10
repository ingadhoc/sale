.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===================
Sale Order Validity
===================

* This module adds allowes to set how many days validity the quotation is.
* By default the number of days of validity is chosen from the company.
* It is posible to modify the numbers of days only if the new number is lower than the one set in the company
* The validation date is calculated as the date the quotation was created + days validty
* If the validaty date is in the past it is not posible to validate de quotation
* A new buton is created to reset the validity date and resete the prices of every line.


Installation
============

To install this module, you need to:

#. Just install this module


Configuration
=============

To configure this module, you need to:
 * Go to Companies.
 * Select a company.
 * In Configuration/Sales set the validate days for this Company.


Usage
=====

To use this module, you need to:

#. You can established the quantity of days to validty the sale order.


.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.adhoc.com.ar/

.. repo_id is available in https://github.com/OCA/maintainer-tools/blob/master/tools/repos_with_ids.txt
.. branch is "8.0" for example

Known issues / Roadmap
======================

* ...

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

* ADHOC SA: `Icon <http://fotos.subefotos.com/83fed853c1e15a8023b86b2b22d6145bo.png>`_.

Contributors
------------


Maintainer
----------

.. image:: http://fotos.subefotos.com/83fed853c1e15a8023b86b2b22d6145bo.png
   :alt: Odoo Community Association
   :target: https://www.adhoc.com.ar

This module is maintained by the ADHOC SA.

To contribute to this module, please visit https://www.adhoc.com.ar.
