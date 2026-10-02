# src/tradingmachine/orders/plan_parts/option_model_pricing.py

`OptionModelPricing` mirrors UBI's `OptionModelPricing`, in `unified_broker_interface/utilities/order_engine/utilities/option_model_pricing.py` in the sibling project, which `PlanReader._read_option_model` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02 and keeps the rules of UBI's `volatility` synthetic type. UBI's class is a subclass of its `FollowInstrumentPricing`; this one is self-contained instead, following the user's rule that each case is its own readable class.

## The JSON shape

```json
{"option_model": {"instrument_id": "dba60324-...", "volatility": 13.0, "interest_rate": 6.5, "lowest": 50.0, "highest": 120.0, "step_ticks": 2}}
```

`instrument_id`, the option's underlying, and `volatility` are required. `volatility` is a percentage above zero and at most `HIGHEST_VOLATILITY_PERCENT`, 500, so 13% is written `13.0`, not `0.13`. `interest_rate` is a yearly percentage defaulting to 0 and may be any finite number. `lowest`, `highest` and `step_ticks` work as in `follow_instrument`.

## Rules that bite

- UBI prices with Black-76. A future as the underlying is treated as the forward, so no interest rate is needed; an index or a share is grown to expiry by `interest_rate`, so leaving it at 0 underprices a call slightly.
- The option's strike, expiry and kind are read from UBI's catalogue when the plan is placed, and an order whose instrument is not an option is refused then with HTTP 400. The offline `PlanReader` does not check that.
- The template's own price is the worst the order accepts, so the `PlanOrder` should be a `limit` with a price.
- The examples find the nearest weekly Nifty contract with `EquityIndexOption.expiries` and `chain`, which are read-only. The index's symbol in UBI is `NIFTY`; `NIFTY 50` is not found.
