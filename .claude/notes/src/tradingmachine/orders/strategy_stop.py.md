# src/tradingmachine/orders/strategy_stop.py

`StrategyStopOrder` mirrors UBI's `strategy_stop` synthetic order type, `unified_broker_interface/utilities/order_engine/strategy_stop.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row F1 strategy-level stop and target.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The class has no instrument argument of its own. UBI's route runs `PlaceOrderRequest` over the body before the engine sees it, so the body needs a resolvable `instrument_id`, and the first candidate's instrument is used for it; the engine then places only the candidates (`utilities/candidate_legs.py`). An empty candidate list therefore raises `ValueError` here, which is the one check in the package, because without a candidate there is no instrument to put in the body and the request could not be built at all. The template's fields become the defaults each candidate overrides, and UBI never resolves price or quantity references for this type, so the class does not accept them. The leak of a template price into a market candidate is described in the note on `order_candidate.py`. `loss_limit` must be below zero and `profit_target` above it, and UBI requires at least one of the two.
