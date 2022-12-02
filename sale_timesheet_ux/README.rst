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

* When confirming a sale order with service products with Service tracking = "Create a task in sales order's project", if the SO has an analytic account that is related to ONE project, then we don't create a project but instead link the new tasks to this project.
* When confirming a sale order with a service product type with service tracking = "Create a task in sales order's project (Project & Task option)", now both the proyect and the task will remain related to the SO when billable is turned off from the proyect settings (works both for a new proyect and task as for a new task in an existing proyect).
* Se protegen las lineas de las ordenes de ventas que estan asociadas a los partes de horas en los siguientes casos (no se borran las horas imputadas a esa linea de la OV) (esta proteccion se habilita desde las configuraciones del parte de horas):

   1) Si a un proyecto se le desmarga el facturable en su configuración: si un proyecto esta como facturable, y tiene tareas con partes de horas asociados a ordenes de venta, al destildarle el facturable la orden de venta seguira teniendo cargadas las horas imputadas en esa tarea.
   2) Se elimina el partner, la cuenta analitica o el item de la orden de venta del proyecto.
   3) Se elimina el partner, la cuenta analitica, el item de la orden de venta o el proyecto de la tarea.
   4) Se elimina el partner, el proyecto, el item de la orden de venta o la cuenta analítica del ticket.
   5) Si se edita manualmente el item de la orden de venta en un parte de horas, entonces se guardará el valor seleccionado de manera manual y no el que trae por defecto el parte de horas.

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
