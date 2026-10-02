# src/tradingmachine/orders/plan_parts/using_part.py

`UsingPart` mirrors UBI's `UsingPart`, in `unified_broker_interface/utilities/order_engine/utilities/using_part.py` in the sibling project, read by `PlanReader._read_using` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`.

## The JSON shape

```json
{"using": {"order": {"execution": [{"twap": {"slices": 4, "over_minutes": 60}}]}, "each_piece": {"presets": [{"bracket": {"stop_price": 990.0, "stop_limit_price": 988.0, "target_price": 1020.0}}]}}}
```

Both values are the contents of an order, not order nodes: UBI checks that `order` and `each_piece` are objects and reads `order["execution"]` directly. The class therefore takes two `OrderPart` objects, for the sake of building them with the same slot parameters as any other order, and unwraps the `order` key from each document. Passing a join as either would raise a `KeyError` in `document()`; that is a misuse of the documented API rather than a validation the library performs.

## How UBI reads it

UBI makes one copy of `order` per piece its execution would send, with `execution` removed and `each_piece`'s values written on, and reads each copy as a whole plan at the path `<path>.pieces.<index>`. `each_piece`'s presets are appended after the order's own; every other slot must appear in only one of the two.

| Rule | Refused as |
|---|---|
| The order's `execution` is a list of exactly one value, `ladder`, `twap` or `front_loaded` (`USING_EXECUTIONS`) | `using_needs_pieces` |
| A timed execution gives `over_minutes`, not `until` (only `vwap` takes `until`, and `vwap` is not allowed anyway) | `using_needs_pieces` |
| `each_piece` takes no `execution` | `using_piece_execution` |
| A slot other than `presets` given in both | `using_slot_twice` |
| A `pricing` in either side beside a `ladder`, because the ladder prices each rung | `using_ladder_priced` |

A ladder's copies each get their rung's price and share, and a timed execution's copies wait `interval * index` from the start through an elapsed condition joined to any trigger they already have. `inner_execution` on the order would make the execution list two long, which UBI refuses.

## Rules that bite

- The join is never resized, so it cannot be a `then` join's child.
- Giving every piece an exit means naming a preset that expands to a `then` join, such as `bracket` or `cover`. A slot-value preset such as `trailing_stop` would instead turn each piece itself into a protecting order rather than following it with one.
