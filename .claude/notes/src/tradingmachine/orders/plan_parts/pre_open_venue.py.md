# src/tradingmachine/orders/plan_parts/pre_open_venue.py

`PreOpenVenue` mirrors UBI's `PreOpenVenue`, in `unified_broker_interface/utilities/order_engine/utilities/pre_open_venue.py` in the sibling project, read by `PlanReader._read_venue_list` and turned into a trigger in `PlanReader._read_order` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. The `opening_auction` preset builds it.

## The JSON shape

A venue is an entry of the order's `venue` list, not a one-key object, so `document()` returns the entry and `OrderPart` wraps it in a list of one:

```json
{"order": {"venue": [{"session": "pre_open", "at_time": "09:02"}]}}
```

`at_time` defaults to `09:00:30` in UBI and must parse as a time of day; the class sends it only when given. Any other key is refused.

## Rules that bite

- UBI sends the order at `at_time` through a `time_from` trigger it builds itself, so the order takes no trigger of its own (`pre_open_sets_its_time`), whether written out or from a preset.
- The pre-open takes only `LIMIT` and `MARKET` orders, on NSE and BSE cash until 09:10 (market orders until 09:05) and on NSE stock and index futures until 09:07. Anything else, or an order taken after collection closed on a trading day, is refused with HTTP 400 when placed; the offline reader does not check that.

The constructor is keyword-only, like the other parts with settings, even though it has one parameter.
