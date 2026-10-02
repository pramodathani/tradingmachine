# src/tradingmachine/orders/plan_parts/position_quantity.py

`PositionQuantity` mirrors UBI's `PositionQuantity`, in `unified_broker_interface/utilities/order_engine/utilities/position_quantity.py` in the sibling project, read by `PlanReader._read_position` and checked with the order's side by `PlanReader._closes_sensibly` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. The `close_on_trigger`, `square_off` and `stop_and_reverse` presets build it.

It is passed to `OrderPart(quantity=...)`, which sends a `PlanPart` quantity as its document.

## The JSON shape

```json
{"position": {"product": "intraday", "instrument_ids": ["e7d0deaa-..."], "ratio": 2, "cancel_resting_first": false}}
```

| Key | UBI's default | How the class sends it |
|---|---|---|
| `product` | the body's product; one of `intraday`, `delivery`, `carry` (UBI's `PRODUCTS`) | sent when not None |
| `instrument_ids` | the order's own instrument; a non-empty list of strings | built from `held_instruments`, each object's `instrument_id` |
| `every_instrument` | `false` | `bool = False`, sent only when True; refused beside `instrument_ids` |
| `ratio` | `1`; only 1 or 2 | sent when not None |
| `cancel_resting_first` | `true` | `bool | None = None`, sent only when not None |

## Rules that bite

- The product is a position product, not an order product: `mis` is refused, `intraday` is right. This is the same naming trap `TradeableInstrument.reduce_position` has.
- The order's side must be `close` (`position_needs_close`), and a `close` side needs this quantity (`close_needs_position`).
- A close takes no pricing or execution of its own (`close_prices_itself`); UBI prices each closing order two ticks past the other side's touch and sends each broker's share to the broker holding it.
- Nothing held ends the plan `completed` without an order.

## Naming

The parameter is called `held_instruments` rather than `instruments`, which would have hidden the imported `tradingmachine.assets.instruments` module inside `__init__`; the name also says which instruments are meant, those whose positions are closed.
