# src/tradingmachine/orders/legged_spread.py

`LeggedSpreadOrder` mirrors UBI's `legged_spread` synthetic order type, `unified_broker_interface/utilities/order_engine/legged_spread.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D9 legged spread with a net-price limit.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI's `LeggedSpread` reads exactly two candidates and a `net_price`. The class takes them as `first_leg` and `second_leg` rather than a list, because the order matters (the first is worked passively and the second is taken as it fills) and a list of exactly two is easy to get wrong. The first leg's instrument anchors the request, as for the other candidate types, and the note on `basket.py` explains why. Only an exchange's own multi-leg order guarantees a net price, which the Atlas lists among the things that cannot be synthesised faithfully, so the docstring warns about the one-legged moment.
