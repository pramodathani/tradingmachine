# src/tradingmachine/orders/plan_parts/__init__.py

The parts live in their own package rather than beside the fifty-four order modules, because they are not order types: none of them can be placed, and putting fifteen more modules in `tradingmachine.orders` would bury the order classes a reader is looking for. Each part has its own module and its own self-contained class, following the user's rule that similar cases are written out one by one rather than through a shared parameterised abstraction, which is also why `TimeAt`, `TimeAfter` and `TimeBefore` are three near-identical classes rather than one class taking a kind.

Every part has a `document()` method returning a dict with exactly one key, the part's UBI name. That one-key shape is what UBI's `PlanReader` requires for nodes, triggers, pricing values and presets alike, and `document()` is the name `OrderCandidate` and `ExposureWatch` already use for the same job. The shared base `PlanPart` exists only so that type annotations can say "any part" and so a forgotten override fails loudly.

Settings left as None are left out of the document, so UBI's own defaults apply, and a boolean that is False is left out too, since False is UBI's default for every boolean in the plan. `OrderPart` sends its one pricing rule inside a list because UBI's format takes a list, reserving room for pricing modifiers in a later stage, and currently refuses more than one rule with the rule `two_setters`.

UBI writes the `fixed` pricing order type in capitals, `LIMIT` or `MARKET`, while the order template takes lower-case `limit` and `market`. The value is passed through unchanged, in keeping with sending UBI's vocabulary as plain strings, and the docstring of `FixedPricing` says so.
