# src/tradingmachine/assets/analysis/math_operators.py

`MathOperators` holds the ten TA-Lib math operators from the old `Instrument`, ported on 2026-09-14. Shared background is in `price_analysis.py.md`.

Method names were spelled out; the column labels keep the old forms.

| Old method | New method | Column labels |
|---|---|---|
| `add` | `add` | `sum` |
| `sub` | `subtract` | `difference` |
| `mul` | `multiply` | `product` |
| `div` | `divide` | `quotient` |
| `max` | `maximum` | `max` |
| `min` | `minimum` | `min` |
| `maxindex` | `maximum_index` | `maxindex` |
| `minindex` | `minimum_index` | `minindex` |
| `minmax` | `minimum_maximum` | `min`, `max` |
| `minmaxindex` | `minimum_maximum_index` | `minindex`, `maxindex` |

The old `max` and `min` also shadowed Python's built-in functions inside the class body, which the new names avoid.

The two-column methods default to `first_column="high"` and `second_column="low"`, as the old ones did. The rolling methods take `column` before `window`, the reverse of most other analysis methods, because the old signatures had that order; call them with keyword arguments.

The label reuse is inherited too: `minimum_maximum` writes the same `min` and `max` columns as `minimum` and `maximum`, so calling them on the same frame overwrites. Each method fetches its own candles, so this only matters when frames are combined by hand.

TA-Lib's index functions return row positions counted from the first candle of the fetched range, not labels of the frame's index.
