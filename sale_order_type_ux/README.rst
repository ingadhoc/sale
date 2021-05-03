.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================
Sale Order Type Ux
===================

* This module adds in the list view of sale.order.type the field sequence to be able to sort by that field.
* We also make type field on sale orders readonly on states different from draft and sent.
* Also add tracking to same field.
* Auto-complete the same Analytic Tag setted on order type.
* Move sale type field after date instead of after currency
* Add new behaivor to the onchage sale type in invoice, to change the company.
* Set in Invoice view form the field "Sale Type" readonly to states different than "draft".
* Add fiscal position on sale types
* Integration betweeen Portal and Sale Order Type module:

 - New access record to sale type model for portal users
 - Make invisible sale order type for portal users

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

#. Just usage.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/{project_repo}/issues>`_. In case of trouble, please
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
