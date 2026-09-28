# src/tradingmachine/asset_baskets/asset_basket.py

`AssetBasket` is the shared base of every basket. It holds only what is genuinely the same for every kind: the members, the list requests to UBI, the weights, the history methods, and the candles for the whole basket. Each kind of basket is its own class in its own file, following the user's rule of self-contained classes over one parameterised abstraction.

## Candles for the basket, so it inherits the analysis

The user chose on 2026-09-28 that a basket should inherit the roughly 190 analysis methods an instrument has. `PriceAnalysis` only needs `prices`, so `AssetBasket.prices` builds candles for the whole basket and inherits the same thirteen analysis classes as `Instrument`, plus `PerformanceMeasures`.

Each candle is the sum over members of a fixed quantity times the member's candle. `_candle_quantities` decides the quantities: the base class spreads `base_value` (100) across the members by weight at the first candle's closes, which is how a price index moves between rebalances; `Portfolio` uses its real quantities; a price-weighted `Index` holds the same quantity of each. The open and close are exact. The high and low are the sums of the members' highs and lows, an upper and lower bound, because the members do not reach their highs at the same moment; the plan and the docstring both say so. Volume and open interest are NaN, because a sum of volumes across different shares has no meaning, so the volume indicators return NaN on a basket.

Only candles every member has are kept, joined on `datetime`. A member listed during the range shortens the basket's history, and a member with no candles at all makes `prices` return None rather than a basket quietly missing it.

Verified on 2026-09-28 with INFY, TCS and WIPRO weighted 50, 30 and 20: the basket's last close of 87.92 over 30 days equalled the weighted sum worked out by hand, the return contributions added up to the cumulative return of -0.30058 exactly, and `relative_strength_index` worked on the basket.

## Live members read the whole basket in one request

`last_prices`, `ohlc` and `quotes` send one `POST` naming every member. A member UBI has no price for gets a row with its `error` filled in rather than failing the call, and a total such as `day_change_percent` is None when any member is missing, following `positions_value`'s rule that a total never quietly leaves a part out. The history methods raise `BasketMemberError` when UBI answers an error for a member, because a history with a member missing would be wrong rather than incomplete.

`_post_for_instruments` sorts the answer by `request_index`, which UBI documents as the way to match entries to the request.

## Why the `instruments` module is imported as `asset_instruments`

The class has a property named `instruments`. Python 3.14 evaluates annotations lazily, and the annotation of a method defined after that property looks names up in the class body first, so `list[instruments.Instrument]` found the property and `annotationlib.get_annotations` raised `'property' object has no attribute 'Instrument'`. Running code was unaffected, but anything that reads type hints would break. The style guide allows `import ... as` when a name clashes, so this one file imports the module as `asset_instruments`. The other basket modules define no `instruments` member of their own and import it normally.

## Why there is no `save` method

The plan gave the basket a `save` method. It was dropped because the basket would have had to import the store, and the store imports every basket class, so the import would have had to go inside the method. Callers write `BasketStore().save(basket)` instead, which is as short and hides nothing.

## Measures chosen

- `risk_contributions` is the standard Euler split: a member's weight times its covariance with the basket, divided by the basket's variance, which adds up to 1.
- `diversification_ratio` is the weighted average of member volatilities over the basket's volatility, Choueifaty's definition.
- `concentration` is the Herfindahl index, and `effective_number_of_members` its inverse.
- `overlap_with` is the sum of the smaller weights, the usual portfolio-overlap test for funds.
- `return_contributions` weights each member's return by its share of the value at the first candle, so the contributions add up to `cumulative_return` exactly.
