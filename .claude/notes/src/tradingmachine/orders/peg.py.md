# src/tradingmachine/orders/peg.py

`PegOrder` mirrors UBI's `peg` synthetic order type, `unified_broker_interface/utilities/order_engine/peg.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row A3 pegged order, and G4 midprice order.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI names the references `own_touch`, `mid` and `opposite_touch` rather than the Atlas's peg-to-primary, peg-to-midpoint and peg-to-market, because the American venue names read backwards to anyone who has not met them. The class uses UBI's names.
