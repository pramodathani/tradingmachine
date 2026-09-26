# src/tradingmachine/orders/__init__.py

The package was added on 2026-09-26 to expose UBI's order engine, which the sibling project gained on 2026-09-23. The user decided three things about its shape.

1. Order types are built in UBI, not here. Nothing in this package places, watches or re-prices an order itself; each class only describes one and sends it.
2. Each synthetic type is its own self-contained class in its own module, following the user's rule that similar cases are written as separate classes rather than one parameterised abstraction. A shallow base class, `SyntheticOrder`, holds only what is identical for every type: storing the template, building the `synthetic` object and sending it.
3. The package is flat. UBI's documentation groups the types into eight families, but its own code keeps them in one flat `order_engine/` directory, and a flat package keeps imports short: `from tradingmachine.orders import bracket`.

## Why there are forty-two classes and not forty-eight

UBI's order engine was designed from the "Synthetic Order Atlas", an artifact at https://claude.ai/artifact/8s91yvX6KfTcrjeu9PPs71. UBI's count of "48 of 52" covers the Atlas's groups A to F, 48 buildable rows and 4 impossible ones. Forty of those rows are classes in UBI's registry (`unified_broker_interface/utilities/order_engine/utilities/registry.py`), and eight need no class: marketable limit and market-to-limit are price references, immediate-or-cancel is `validity`, stop-market and stop entry are plain `sl` orders, one-updates-other is how every linked type behaves, the kill switch is `POST /api/orders/flatten`, and the daily loss lockout is an engine setting. The registry holds 42 classes because it adds `simple` and `virtual_limit`, which are not Atlas rows. This package mirrors the registry, so it has 42 classes too. The eight classless rows are reached through `place_order`'s arguments, the price wrappers, `tradingmachine.accounts.account.Account.flatten` and `LossLockoutError`.

The Atlas's group G, seventeen further types from a second sweep of broker catalogues, is outside UBI's count and mostly not built in UBI. Following the user's rule, it is not built here either; the gaps are for the sibling project.

## Naming

The module and class names spell out UBI's abbreviations, as the user's rules require: `oto` is `one_triggers_other`, `oco` is `one_cancels_other`, `oca` is `one_cancels_all`, `gtt` is `good_till_triggered`, `twap` and `vwap` are `time_weighted_average_price` and `volume_weighted_average_price`, and `atr_trail` is `average_true_range_trail`. Every class name ends in `Order`, so a class is never confused with a module of the same stem. The parameter names equal UBI's field names, so UBI's documentation can be read against the classes directly, with two kinds of exception: `atr_multiple` is spelled out as `average_true_range_multiple`, and a field that names an instrument by id takes the instrument object instead, such as `watch_instrument` for `watch_instrument_id`.

Nothing is imported in `__init__.py`, for the same reason as the top-level package: importing the library should not reach for the network or the databases. The docstring holds the table of type, module and class instead, because it is the one place a reader looks for it.
