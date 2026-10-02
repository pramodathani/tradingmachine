# src/tradingmachine/orders/trailing_entry.py

`TrailingEntryOrder` mirrors UBI's `trailing_entry` synthetic order type, `unified_broker_interface/utilities/order_engine/trailing_entry.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B9 trailing entry.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

It shares UBI's trailing mechanism with `trailing_stop`, in `utilities/trailing.py`, and takes the same fields.

## `activate_at`, added on 2026-10-02

UBI's `trailing_entry`, `trailing_stop` and `atr_trail` share one base class, `TrailingOrder` in `unified_broker_interface/utilities/order_engine/utilities/trailing.py`, and none of the three overrides its `run`, so all three read `activate_at` and, when it is given, hold the order until the last traded price reaches that level, answering HTTP 202 with an `outcome` of `armed`. UBI's preset table says `trailing_entry` takes the same settings as `trailing_stop`, which lists `activate_at`. The setting was found missing here in the audit of 2026-10-02 and added under UBI's own name.
