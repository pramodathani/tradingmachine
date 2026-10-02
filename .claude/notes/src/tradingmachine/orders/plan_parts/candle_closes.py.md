# src/tradingmachine/orders/plan_parts/candle_closes.py

`CandleCloses` mirrors UBI's `CandleClosesCondition`, in `unified_broker_interface/utilities/order_engine/utilities/candle_closes_condition.py` in the sibling project, read by `PlanReader._read_candle_closes` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. It keeps the rules of the `candle_close_stop` synthetic type, whose preset builds this condition.

## The JSON shape

```json
{"candle_closes": {"level": 995.0, "direction": "at_or_above", "bar_minutes": 15}}
```

| Setting | Required | UBI's default | UBI's check |
|---|---|---|---|
| `level` | Yes | None | A number above zero, read as a Decimal |
| `direction` | No | From the opening side | `at_or_above` or `at_or_below` |
| `bar_minutes` | No | 5 | A number above zero; the reader's message calls it seconds, but the condition multiplies it by 60, so it really is minutes |

Any other key is refused as an unknown setting. Settings left as None are left out so UBI's defaults apply.

## Rules that bite

- The bars are built by the engine from the last traded price it sees, aligned to the clock, and kept in the condition's memory, so nothing is known until the first whole bar after the order rests has closed. A plan placed at 10:02 with five-minute bars can first fire at 10:10, not 10:05.
- It answers once per bar, at the close, so it is slower than a touch by design.
- With no direction, the direction follows the side that opened the position, not the side the order is sent on: a long (opened with a buy) waits for a close at or below the level and a short for one at or above it. That is a stop's meaning, so for a breakout entry give the direction explicitly, as the breakout example does.
