
## `hold_limits` and `same_as_first` (2026-10-05)

UBI added both on 2026-10-03. An order's own `hold_limits` decides for that order over the plan's, and it is the only way to hold a follow-on order in a Then join's child or an order on the `protect` side, since the request's value deliberately never reaches those. UBI refuses True with the rule `not_holdable` and a reason for an order that cannot be held, such as a market order, one priced by anything but `fixed`, or a leg of a `group_margin` join. `same_as_first` is a new side for a Then join's child, trading on the side the first plan filled on; it needs no code here because `side` is passed through as a string.

`FixedPricing`'s `order_type` must be upper case, `LIMIT` or `MARKET`, since UBI refuses `limit` there with `bad_setting`, unlike the order body, which UBI accepts in any case. The example program `held_entry_and_held_target.py` gives only a price for that reason.
