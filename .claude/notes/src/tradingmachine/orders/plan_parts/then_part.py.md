# src/tradingmachine/orders/plan_parts/then_part.py

`ThenPart` mirrors UBI's `ThenPart`, in `unified_broker_interface/utilities/order_engine/utilities/then_part.py` in the sibling project.

## Exits that follow a position that turned over (2026-10-06)

UBI's commit `8247bb7` of 2026-10-05 fixed two things about a Then join's exits, and the module docstring was updated to say so on 2026-10-06.

When both sides of a two-sided entry filled and the later side filled more, UBI used to resize the exits to the net quantity but leave them on the old side, so a short of 6 kept sell exits that would have doubled it. The exits on the wrong side are now cancelled and sent again on the new side, priced from the fills on the side now held, which is also why `FromFillPricing` counts only that side's fills.

An exit that had finished used to be reopened whenever its part was marked done as cancelled, so a bracket's stop cancelled by its `order_id` was placed again as soon as the cancel was confirmed, and each exchange cancel of a target placed another until one was rejected. A finished exit is now sent again only once its target grows past the target it had when it finished, which UBI records as `done_at_target`.

UBI's commit `15380c1` of the same day also made a refused or rejected child cancel the rest of the first plan and end the parent `failed`, naming the part, rather than `completed` with the position unhedged.
