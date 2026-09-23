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

The big number is always the price with taxes and the small one below is the
price without them, no matter whether the product taxes are set as included in
price or not. When both match (no taxes, or a 0% tax) the small line is hidden.

URL forms
=========

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - URL
     - Company
     - Pricelist
   * - ``/price-checker``
     - current website's (or public user's)
     - company's configured pricelist
   * - ``/price-checker/-/<pricelist_id>``
     - current website's (or public user's)
     - that pricelist (override)
   * - ``/price-checker/<company_id>``
     - that company
     - company's configured pricelist
   * - ``/price-checker/<company_id>/<pricelist_id>``
     - that company
     - that pricelist (override)

The ``-`` placeholder means "default company". On a multi-company database
the bare URL resolves to the website's company, which is not necessarily the
one being configured: use the *Open Price Checker* button in the settings to
get the URL of the right company. Any invalid id, archived
company / pricelist, or pricelist that doesn't belong to the company
returns **404**.

Configuration
=============

#. *Sales → Settings → Price Checker Pricelist* — pricelist used by the
   checker for the active company. Empty → falls back to the product's
   Sales Price. The setting only shows when *Pricelists* is enabled. The
   *Open Price Checker* button next to it opens the checker of the company
   being configured.

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
