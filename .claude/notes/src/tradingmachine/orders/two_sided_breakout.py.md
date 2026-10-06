# src/tradingmachine/orders/two_sided_breakout.py

`TwoSidedBreakoutOrder` mirrors UBI's `two_sided_breakout` synthetic order type, `unified_broker_interface/utilities/order_engine/two_sided_breakout.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D8 two-sided breakout.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

Both entries are native stops, so the template usually has `order_type` `sl`; UBI builds the two entries from `buy_trigger`, `buy_limit`, `sell_trigger` and `sell_limit`. UBI never resolves references for this type. The exits are armed after the break on the side that filled.

## Exits became distances from the fill, on 2026-10-02

The class first sent its exits as the absolute `stop_price`, `stop_limit_price` and `target_price`, as `oco` takes them. UBI's commit `42ba13d` of 2026-10-02 found that this was dangerous: one absolute target cannot suit a break either way, so after a break downwards a target above the range bought straight back and closed the short at once. UBI now takes `stop_distance` with `stop_limit_offset`, and `target_distance`, each measured from the entry's average fill in the direction of whichever side broke and rounded to the tick, and it refuses the three absolute fields with HTTP 400. At least one of the two distances must be given, and a stop without `stop_limit_offset` is refused, because a stop-limit whose limit sits at its trigger will not fill when the price runs through it. The class's parameters were renamed to UBI's new field names the same day, so a caller who still passes `stop_price` gets a `TypeError` from Python rather than a refusal from UBI.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `8247bb7` fixed the exits after both sides of a breakout filled. When the later side filled more, the exits were resized to the net quantity but left on the old side, so a short of 6 kept sell exits that would have taken it to 12, and they were measured from an average of the buy and sell fills. Exits on the wrong side are now cancelled and sent again on the new side, measured from the fills on the side now held. UBI's commit `15380c1` made a refused order in a Then join's child cancel the rest of the first plan and end the parent `failed`, and since a breakout's exits are such a child, the docstring now says so.
