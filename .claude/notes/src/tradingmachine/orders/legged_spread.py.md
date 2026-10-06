# src/tradingmachine/orders/legged_spread.py

`LeggedSpreadOrder` mirrors UBI's `legged_spread` synthetic order type, `unified_broker_interface/utilities/order_engine/legged_spread.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D9 legged spread with a net-price limit.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI's `LeggedSpread` reads exactly two candidates and a `net_price`. The class takes them as `first_leg` and `second_leg` rather than a list, because the order matters (the first is worked passively and the second is taken as it fills) and a list of exactly two is easy to get wrong. The first leg's instrument anchors the request, as for the other candidate types, and the note on `basket.py` explains why. Only an exchange's own multi-leg order guarantees a net price, which the Atlas lists among the things that cannot be synthesised faithfully, so the docstring warns about the one-legged moment.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `cfdcad7` changed how the second leg is sized and priced. It used to be priced from the first leg's cumulative average alone, so each top-up priced from an earlier average left the spread away from `net_price` (20.65 against 20 in one of UBI's runs), and a price such as 982.05 on a 0.10 tick was refused by the broker and the refusal swallowed. Each new order is now priced so that the second leg's orders together average what the net needs, rounded to the second leg's tick in the caller's favour. It used to be sized to the first leg's filled quantity, which a future with a lot of 500 or a Sensex option against a Nifty one refused; it is now a whole number of lots of its own instrument, rounded to the nearest lot. Its instrument is read when the order arrives, so an unmapped one is refused with HTTP 404 before the first leg is sent. UBI's commit `15380c1` then made a refused second leg cancel the rest of the first and end the parent `failed`. The docstrings describe all of this; the second candidate's own quantity, price and order type are not used, which the `second_leg` argument now says.
