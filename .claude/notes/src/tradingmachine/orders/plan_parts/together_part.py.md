# src/tradingmachine/orders/plan_parts/together_part.py

`TogetherPart` mirrors UBI's `TogetherPart`, in `unified_broker_interface/utilities/order_engine/utilities/together_part.py` in the sibling project, read by `PlanReader._read_together`, which hands the list to `PlanReader._read_children`, in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. UBI's `basket` preset expands to this join, one child per candidate, with `group_margin` on.

## The JSON shape

```json
{"together": {"children": [{"order": {}}, {"order": {}}], "group_margin": true, "hedge_benefit": true, "done_when": "any"}}
```

| Key | UBI's default | How the class sends it |
|---|---|---|
| `children` | required, 1 to 25 plans (`MOST_CHILDREN`) | always |
| `group_margin` | `true` | `bool | None = None`, sent only when not None, because UBI's default is True |
| `hedge_benefit` | `false` | `bool = False`, sent only when True |
| `done_when` | `all`; the other value is `any` (UBI's `DONE_WHEN`) | sent only when not None |

Any other key is refused as `unknown_setting`, and a non-boolean flag or an unknown `done_when` as `bad_setting`.

## Rules that bite

- Each child trades its own quantity, so a child with no `quantity` of its own uses the body's. Nothing ties the children's sizes together; for that, use an `either` join with `reduce`.
- Only the first child's main order carries the caller's tag (`keeps_tag and index == 0` in `_read_children`).
- A together join cannot be a `then` join's child (`join_not_sized`), because that child is sized to the first plan's fills.
- Unlike `sequence`, a together join accepts a single child; UBI's smallest for it is 1.
- `hedge_benefit` matters only to the broker selector's affordability check; it prices options and futures on one underlying and expiry together, as the `basket` type does.

The children are kept as a list built from the sequence given, so a caller's later change to their own list does not alter the join, matching `EitherPart`.
