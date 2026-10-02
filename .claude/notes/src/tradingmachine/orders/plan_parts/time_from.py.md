# src/tradingmachine/orders/plan_parts/time_from.py

`TimeFrom` mirrors the `time_from` kind of UBI's `TimeCondition`, in `unified_broker_interface/utilities/order_engine/utilities/time_condition.py` in the sibling project, which `PlanReader._read_condition` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds for any key in `KINDS` whose value is a string. It was written on 2026-10-02 as an exact copy of `time_at.py` and `time_after.py`, taking the time as its one positional argument, because the four time conditions differ only in their key.

## The JSON shape

```json
{"time_from": "15:00"}
```

The value must be a string; anything else is refused with `bad_setting`. UBI accepts `HH:MM` or `HH:MM:SS`, read in India's time.

## How it differs from time_at and time_after

`time_at` and `time_after` work out the moment once, when the plan is placed, and a time already passed on a trading day is refused with HTTP 400. `time_from` checks first whether today is a trading day for the instrument and the time has passed; if so it holds at once from the moment of placing, and otherwise it falls back to the same next-trading-day rule as `time_at`. That is why UBI uses it for the `closing_price` preset, which starts at once when placed inside its window, and for the pre-open venue, whose `at_time` is turned into a `time_from` trigger by the reader. The rejection only happens at placement time, so the offline `PlanReader` accepts a passed `time_at` too; the difference cannot be seen without placing an order.
