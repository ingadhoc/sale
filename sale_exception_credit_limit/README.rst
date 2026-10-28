.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===========================
Sale Exception Credit Limit
===========================

#. It blocks the confirmation of a sale order when the customer goes over its credit limit, through a 'Credit Limit Exceeded' exception rule.
#. It adds a 'Credit Taken' field on the partner that, unlike the native credit, also counts confirmed sale orders that are not invoiced yet and draft invoices, over the whole company tree.
#. It adds a new group 'Config Credit Limit On partners'. Only users with this group can change the credit limit parameters of a partner, unless the partner is a child copying the limit of its parent.
#. A credit limit equal to zero means that the partner has not credit limit. The precision of comparison depends on currency decimal places.
#. It hides the native default credit limit on the accounting settings, so the limit is always the one set on each partner, and lets the 'Sales Credit Limit' setting be changed only on the root company. A child company follows its parent.

Installation
============

To install this module, you need to:

#. Only need to install the module. On installation it turns the 'Sales Credit Limit' setting on for every company.


Configuration
=============

To configure this module, you need to:

#. Add the users that may change credit limits to the 'Config Credit Limit On partners' group, on their user profile.
#. Set the credit limit of each customer on its form, with 'Partner Limit' on.


Usage
=====

To use this module, you need to:

#. When you confirm a sale order, the credit taken by the customer, including this order, is checked against its credit limit. Over the limit, the order is not confirmed and the exception is shown.

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
