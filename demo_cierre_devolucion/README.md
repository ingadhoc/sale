# Spike — do not merge

Experimental modules for task 72096. They are **not** meant to be merged into
20.0: they exist so the proposal can be reviewed and tried on a test database
instead of living on someone's laptop.

Three modules, installed in this order:

| Module | What it does |
|---|---|
| `demo_cantidad_devuelta` | Returned quantity as an informative column only: computed, not stored, with no depends on invoicing or delivery. |
| `demo_cancelar_remanente` | The usual "cancel remaining" button, with the new arithmetic: ordered = delivered, instead of delivered + returned. |
| `demo_cierre_devolucion` | Asks, when validating a return, whether to close the order by what was delivered or leave it pending for replacement. Plus a check when creating the invoice. |

## Why

Today the returned quantity is subtracted in five computed fields across nine
modules, so the system has to *infer* whether a return closes the order or
expects a replacement. It cannot know, and that is where the quantity bugs come
from.

These modules take the opposite approach: **no computed field is intercepted**.
The question is asked once, through `stock.picking._pre_action_done_hook()` —
the same native mechanism behind the backorder wizard — and the answer is stored
on the return picking.

## Status

Verified on a clean Odoo 20 Enterprise database: one, two and three step
deliveries, chained and sequential document creation, kits, subscriptions,
multiple returns, the exchange button, and purchases. **Not** tested alongside
the existing Adhoc modules that touch the same computations.
