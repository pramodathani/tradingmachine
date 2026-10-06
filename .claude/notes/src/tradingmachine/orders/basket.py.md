# src/tradingmachine/orders/basket.py

`BasketOrder` mirrors UBI's `basket` synthetic order type, `unified_broker_interface/utilities/order_engine/basket.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D10 basket order.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The class has no instrument argument of its own. UBI's route runs `PlaceOrderRequest` over the body before the engine sees it, so the body needs a resolvable `instrument_id`, and the first candidate's instrument is used for it; the engine then places only the candidates (`utilities/candidate_legs.py`). An empty candidate list therefore raises `ValueError` here, which is the one check in the package, because without a candidate there is no instrument to put in the body and the request could not be built at all. The template's fields become the defaults each candidate overrides, and UBI never resolves price or quantity references for this type, so the class does not accept them. The leak of a template price into a market candidate is described in the note on `order_candidate.py`. A dry run of a basket prepares only the first candidate, so it cannot show that a later candidate is wrong.

## `hedge_benefit`, added on 2026-10-02

UBI added the optional boolean `hedge_benefit` to `basket` on 2026-09-30, in its commit `38de0f3`, when the lowest-cost broker selector began passing over brokers that cannot afford an order. With it, UBI prices options and futures on one underlying and expiry together as a hedged whole when it checks that a broker can afford the basket, so a hedged position such as an iron condor is not refused for margin it would never need. Without it, every leg's margin is added up. The class sends the field only when it is True, as the base class does for `reduce_only`, so UBI's default applies otherwise.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `15380c1` changed what happens when a leg is refused after another leg has already gone to a broker. A refusal with HTTP 503, such as a contract size the brokers disagree on, used to escape, so the answer said nothing was sent, the parent was stored `rejected` and the live leg was left with nobody watching it. Any refusal beside live orders now ends only the refused leg, and the answer is HTTP 207 with the placed legs still watched.
