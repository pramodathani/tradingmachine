# src/tradingmachine/orders/scale_with_profit_taker.py

`ScaleWithProfitTakerOrder` mirrors UBI's `scale_with_profit_taker` synthetic order type, `unified_broker_interface/utilities/order_engine/scale_with_profit_taker.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G15 scale with profit-taker. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI builds it on its `ladder` type, so `from_price`, `to_price` and `steps` carry the ladder's own limits and descriptions. It never finishes on its own, which is why the class docstring points at `cancel()`.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `d3a354c` shared the rungs out in whole lots, as for `ladder`, and sized each profit-taker from what its rung actually filled rather than from the rung's planned size, because a rung the caller cut to 5 that filled 5 used to get a profit-taker of 10 and leave the account short 5. The same commit corrected UBI's description of `most_cycles`: UBI's code counts how many times a rung has been placed again and stops once that count reaches `most_cycles`, so each rung trades `most_cycles + 1` times, and the parent completes once every rung has used its cycles. The earlier docstring's "up to `most_cycles` times per rung" and "may go round" read as the total number of trades, so both the description and the `most_cycles` argument were rewritten. UBI's commit `8c86310` stopped one refused profit-taker from marking a working parent `rejected` while its other rungs rested, which had also made the parent impossible to cancel.
