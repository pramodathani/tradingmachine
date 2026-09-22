# src/tradingmachine/assets/analysis/price_transforms.py

`PriceTransforms` holds the four TA-Lib price transforms from the old `Instrument`, ported on 2026-09-14 with unchanged names and column labels (`avg_price`, `med_price`, `typ_price`, `wght_close`). Shared background is in `price_analysis.py.md`.

`average_price` here is TA-Lib's average of each candle's open, high, low and close. It is unrelated to the `average_price` field in UBI's quote, which is the day's volume weighted average price and is read by `TradeableInstrument.volume_weighted_average_price`.
