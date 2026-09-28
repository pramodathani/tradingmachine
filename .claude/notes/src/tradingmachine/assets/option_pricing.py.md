# src/tradingmachine/assets/option_pricing.py

This module holds `BlackScholes`, the pricing model behind `Option.implied_volatility` and `Option.greeks` in `src/tradingmachine/assets/instruments.py`. It was added on 2026-09-28 with the derivative base classes.

## Why the greeks are computed here and not in UBI

UBI has no route for greeks, implied volatility or an option chain with prices. The user decided on 2026-09-26 that order types belong in UBI, and on 2026-09-28 chose to compute greeks locally anyway, because they are analysis rather than order behaviour. They sit alongside the TA-Lib indicators, which are also worked out here from UBI's raw figures, and nothing about them changes what order is sent.

It is a module of its own, rather than part of `instruments.py`, because the maths does not depend on UBI at all and can be used and checked with any figures. It imports only `math`, so `instruments.py` can import it without a cycle.

## The model and its conventions

The model is Black-Scholes for a European option with no dividends. With S the underlying price, K the strike, T the years to expiry, r the risk-free rate, σ the volatility, N the standard normal cumulative distribution and n its density:

| Quantity | Formula |
|---|---|
| d1 | (ln(S / K) + (r + σ² / 2) T) / (σ √T) |
| d2 | d1 − σ √T |
| Call price | S N(d1) − K e^(−rT) N(d2) |
| Put price | K e^(−rT) N(−d2) − S N(−d1) |
| Delta | N(d1) for a call, N(d1) − 1 for a put |
| Gamma | n(d1) / (S σ √T) |
| Theta | (−S n(d1) σ / (2 √T) ∓ r K e^(−rT) N(±d2)) / 365 |
| Vega | S n(d1) √T / 100 |
| Rho | ± T K e^(−rT) N(±d2) / 100 |

The units follow what brokers' option chains show, which is what a trader will compare against. Theta is per calendar day, so the annual figure is divided by 365. Vega is per percentage point of volatility and rho per percentage point of the rate, so both are divided by 100. N is computed with `math.erf`, which is exact enough and needs no third-party package.

The constructor refuses an underlying price, strike, time or volatility that is not above zero with `ValueError`, because the formulas divide by or take the logarithm of each. That is a precondition of the maths, not the kind of order validation this project leaves to UBI.

## Implied volatility

`implied_volatility` is a class method because an instance needs a volatility to exist, and the search is looking for exactly that value. It bisects between `LOWEST_VOLATILITY` (0.0001) and `HIGHEST_VOLATILITY` (5.0, which is 500 per cent) for `SEARCH_STEPS` (100) rounds, building one `BlackScholes` per step and comparing its price. A model's price rises steadily with volatility, so bisection always converges, and 100 halvings of a range of 5 is far finer than any tick.

It returns None rather than raising when there is nothing to find: a premium that is not above zero, one below the model's price at the lowest volatility, which means it is below the discounted intrinsic value, or one above the price at the highest volatility. These bounds mirror UBI's own search in `unified_broker_interface/utilities/order_engine/utilities/black76.py`, so the two give up in the same places.

## Black-Scholes here, Black-76 in UBI

UBI's order engine prices options with Black-76 on the forward price, for its `volatility` and `attached_hedge` synthetic orders. This module uses Black-Scholes on the spot price. For an option on a share with no dividend due before expiry the two agree, and for an index option they differ slightly, because Black-76 takes the forward and the index's dividends make the forward a little lower than the carry formula implies. Anyone comparing `Option.implied_volatility` with the volatility UBI's engine reports should expect a small gap and not read it as a bug in either.

`DEFAULT_RISK_FREE_RATE` is 0.065, an approximation of India's 91-day treasury bill yield in 2026. It is a default a caller should override when the rate matters, not a figure the library keeps current.

## Checked offline on 2026-09-28

A scratchpad script compared the model with values computed independently for S = 100, K = 100, T = 1, r = 0.05 and σ = 0.2. Every value agreed to four decimal places.

| Quantity | Call | Put |
|---|---|---|
| Price | 10.45058 | 5.57353 |
| Delta | 0.63683 | −0.36317 |
| Gamma | 0.01876 | 0.01876 |
| Vega | 0.37524 | 0.37524 |
| Theta per day | −0.01757 | −0.00454 |
| Rho | 0.53232 | −0.41890 |

Put-call parity held, since 10.45058 − 5.57353 = 4.87706 = 100 − 100 e^(−0.05). `implied_volatility` recovered 0.2000004 from the call price and 0.1999993 from the put price, returned None for premiums of 0, 0.001 and 99, and a time to expiry of zero raised `ValueError`.
