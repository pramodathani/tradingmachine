# src/tradingmachine/orders/ladder.py

`LadderOrder` mirrors UBI's `ladder` synthetic order type, `unified_broker_interface/utilities/order_engine/ladder.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row E3 scaled or ladder order.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI never resolves price or quantity references for a ladder (`docs/rest-api/price-quantity-references.md`), so a template carrying only a `price_reference` would go out at price 0. The class does not refuse one, in line with the rule that nothing is validated locally, and its docstring says to give real numbers.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `d3a354c` made the ladder share its quantity out in whole lots of the instrument, the first rungs taking the remainder, and refuse with HTTP 400 a quantity of fewer lots than steps. Before, 225 on a lot of 75 over two steps was split as 113 and 112, which the broker refused, and a held scale order built on the same split stalled silently in `received`. The `steps` argument now says the quantity must be at least that many lots. UBI's code divides the quantity by the lot with whole-number division, so a quantity that is not a whole number of lots appears to lose its remainder; that was read from the code and not tested, so the docstring does not claim it.
