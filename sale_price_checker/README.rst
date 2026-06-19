.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==================
Sale Price Checker
==================

Public web price checker for in-store kiosks: scan a barcode, see the price
(taxes included). The screen auto-resets 5s after each scan.

URL forms
=========

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - URL
     - Company
     - Pricelist
   * - ``/price-checker``
     - first active by ``sequence``
     - company's configured pricelist
   * - ``/price-checker/-/<pricelist_id>``
     - first active by ``sequence``
     - that pricelist (override)
   * - ``/price-checker/<company_id>``
     - that company
     - company's configured pricelist
   * - ``/price-checker/<company_id>/<pricelist_id>``
     - that company
     - that pricelist (override)

The ``-`` placeholder means "default company". Any invalid id, archived
company / pricelist, or pricelist that doesn't belong to the company
returns **404**.

Configuration
=============

#. *Sales → Settings → Price Checker Pricelist* — pricelist used by the
   checker for the active company. Empty → falls back to the product's
   Sales Price. The setting only shows when *Pricelists* is enabled.

#. *Products list view* — optional column *Show in Price Checker* (default
   ``True``) to hide / show products in the checker.

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
