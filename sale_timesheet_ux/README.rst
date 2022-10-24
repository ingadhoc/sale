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
* Incorporar protección de cambios en partes de hora:
a) Odoo, mediante distintos mecanismos, puede modificar la sale line vinculada a una linea de parte de horas.(campo so_line de account.analytic.line). Esto pasa si cambia
   1. billiable de proyecto
   2. empleado
   3. la linea de venta en tarea, ticket o proyecto asociados al parte de horas. Estos a su vez cambian si:
      3.1 en ticekts, si cambia: commercial partner, team_id.use_helpdesk_sale_timesheet, project_id.pricing_type o project_id.sale_line_id
      3.2 en tareas: commercial_partner_id', 'sale_line_id.order_partner_id.commercial_partner_id', 'parent_id.sale_line_id', 'project_id.sale_line_id
      3.3 en proyectos: si cambai el partner
   4. Cuando se modifica manualmente la so_line de un parte de horas, mediante javascript, odoo marca el campo is_so_line_edited y a partir de ahí queda protegida
b) el tema de la protección de a4 no protege en dos casos:
   1. desmarcar allow billiable de un proyecto: esto casi que pareciera ser un bug y, sin importar si las lineas estan manuales o no, desmarca lo facturado en todas las lineas asociadas a este proyecto
   2. para el resto de los casos la protección va bien pero solo se protege cuando la linea se edita manualmente, por lo cual, para partes de horas creados y donde se deja el valor por defecto la protección NO funciona
c) por todo lo anterior implementamos en este modulo dos mejoras:
   1. Con solo instalar este modulo mejoramos que si se desmarca en un proyecto el allow_billable SOLO se limpien la lineas que no estan editadas manualmente porque ese dato no se recupera

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
