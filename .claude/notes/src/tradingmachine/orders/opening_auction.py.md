# src/tradingmachine/orders/opening_auction.py

`OpeningAuctionOrder` mirrors UBI's `opening_auction` synthetic order type, `unified_broker_interface/utilities/order_engine/opening_auction.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G1 market-on-open and limit-on-open. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI decides which instruments have a pre-open and refuses the rest, so the class does not repeat the table of which segments and cut-off times qualify; the docstring describes it only so a caller knows before sending.
