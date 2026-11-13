.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================
Sale Order Type Report Partner
==============================

Prints the sale order report header with the data of a partner chosen on the
sale order type, instead of the data of the company.

It is meant for companies that sell under more than one commercial brand with a
single legal entity: the brand changes with the order type, the invoicing
company does not.

The module has no dependency on any localization, so the behaviour is the same
on every country.

Installation
============

To install this module, you need to:

#. Just install this module

Configuration
=============

To configure this module, you need to:

#. Go to Sales / Configuration / Sale Order Types
#. Open the type you want to print with another header
#. Set the "Report Partner" field with the partner of that brand
#. Load the brand logo on the image of that partner

Usage
=====

To use this module, you need to:

#. Create a sales order and set the configured type on it
#. Print the quotation or the order

The header of the report shows the name, the address, the phone and the tax id
of the report partner, and its image as the logo. Everything else on the
report, and every other report, is left untouched. A type without a report
partner keeps printing the company data.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Known issues / Roadmap
======================

* Only the sale order report reads the field. The invoice and the delivery
  reports keep printing the company data.
* The logo is swapped with one inheritance per report layout, because the
  layouts of ``web`` render ``company.logo`` inline and share no template for
  it. A new layout added by Odoo needs its own inheritance here.

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
