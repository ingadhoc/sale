.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==================
Sales Timesheet UX
==================

* When confirming a sale order with a product with Product Type = "Service" and Create on Order = "Project & Task", if the SO has project, then the system won't create a new project but use the project associated to the SO to create the task inside.
* When confirming a sale order with a product with Product Type = "Service" and Create on Order = "Project & Task", the project and the task will remain related to the SO and the customer will remain related to the project (stays related in the backend even though is hidden by default) when "Billable" is turned off from the project settings (works both for a new proyect and task as for a new task in an existing proyect).
* When (and only when) "Billable" is active can't be edited. Instead adds a button to change its value with an alert message to confirm the disabling of the "Billable" option in the project settings. The message also warns when the project is linked to products that create tasks in it, because they are unlinked. Removing the customer of the project does not switch "Billable" off.
* When the sales order item of a task is changed and saved, a confirmation says how many of its timesheet entries will be recalculated (the ones not chosen by hand, validated or invoiced). It can be discarded.
* A task without sales order item takes it from its parent task, its project or its milestone.
* The sales order also lists the tasks linked to it through the "Related Sales Order" field of the task.
* Sales order lines linked to timesheets are protected: the hours logged on the sales order line are not removed (this protection is enabled from the timesheet settings, "Protect SO Line on Timesheets?"). It applies in these cases:

  1) When "Billable" is turned off in a project: if a billable project has tasks with timesheets linked to sales orders, the sales order keeps the hours logged on those tasks.
  2) When the partner, the analytic account or the sales order item is removed from the project.
  3) When the partner, the analytic account, the sales order item or the project is removed from the task.
  4) When the partner, the project, the sales order item or the analytic account is removed from the ticket.
  5) When the sales order item is edited by hand in a timesheet, the value chosen by hand is kept instead of the default one.

Installation
============

To install this module, you need to:

#. Just install module.

Configuration
=============

To configure this module, you need to:

#. Nothing to configure

Usage
=====

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
