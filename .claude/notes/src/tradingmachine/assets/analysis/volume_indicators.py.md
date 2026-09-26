# src/tradingmachine/assets/analysis/volume_indicators.py

`VolumeIndicators` holds the three TA-Lib volume indicators from the old `Instrument`, ported on 2026-09-14. Shared background is in `price_analysis.py.md`.

| Old method | New method |
|---|---|
| `chaikin_ad_line` | `chaikin_accumulation_distribution_line` |
| `chaikin_ad_oscillator` | `chaikin_accumulation_distribution_oscillator` |
| `on_balance_volume` | unchanged |

The column labels `chaikin_ad`, `chaikin_adosc<fast>_<slow>` (no underscore before the fast period) and `obv` are unchanged.

UBI's candle `volume` is a whole number, or null where a value overflowed. TA-Lib 0.6.8 accepts whole-number pandas columns without conversion, checked on 2026-09-14, so no cast to float is needed.

## Missing volume, noted on 2026-09-26

UBI stores volume as null for some candles. TA-Lib treats a NaN input as poisoning every later value of a running total, so OBV, the accumulation/distribution line and its oscillator, and `momentum_indicators.money_flow_index` return NaN from the first missing volume onwards. The methods pass the `volume` column to TA-Lib as it is. A caller that wants a missing volume counted as zero, as instruments_explorer does, fills it before building the frame.
