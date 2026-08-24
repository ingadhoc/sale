.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

====================================
Portal Distributor Sale with Project
====================================

This module integrate portal sale distributor using sale_project.

#. Add a model access rule so portal distributor users can read project tasks.
#. Extend the groups of the task fields sale_project adds to the sale order
   (tasks_ids, tasks_count and closed_task_count), which are restricted to
   project users. Without this the product catalog can not be opened, because
   loading the order reads those fields.

Installation
============

To install this module, you need to:

#. Just install this module. It is auto installed when both 'Portal Sale
   Distributor' and 'Sales - Project' are installed.

Configuration
=============

To configure this module, you need to:

#. The same as 'Portal Sale Distributor' module.

Usage
=====

To use this module, you need to:

#. Log in with a user with the portal distributor group.
#. Go to Sales and open or create a sales order.
#. Open the product catalog from the order lines.

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
