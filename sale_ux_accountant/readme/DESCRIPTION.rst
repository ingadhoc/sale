Glue module between ``sale_ux`` and ``account_accountant`` (Odoo Enterprise).

It adds the deferred revenue/expense columns (``deferred_start_date`` and
``deferred_end_date``) to the *Invoice Lines* page of the sale order line form.

These fields are defined by the Enterprise ``account_accountant`` module, so
they cannot live directly in ``sale_ux`` (it would break the view parsing on
Community installations). This module is ``auto_install``, so the columns show
up automatically whenever both ``sale_ux`` and ``account_accountant`` are
installed, and never get in the way on Community-only databases.
