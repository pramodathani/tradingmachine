# src/tradingmachine/assets/analysis/math_transforms.py

`MathTransforms` holds the fifteen TA-Lib math transforms from the old `Instrument`, ported on 2026-09-14. Shared background is in `price_analysis.py.md`.

Method names were spelled out; the column labels keep the old short forms.

| Old method | New method | Column label |
|---|---|---|
| `acos` | `arc_cosine` | `acos` |
| `asin` | `arc_sine` | `asin` |
| `atan` | `arc_tangent` | `atan` |
| `ceil` | `ceiling` | `ceil` |
| `cos` | `cosine` | `cos` |
| `cosh` | `hyperbolic_cosine` | `cosh` |
| `exp` | `exponential` | `exp` |
| `floor` | `floor` | `floor` |
| `ln` | `natural_logarithm` | `ln` |
| `log10` | `logarithm_base_10` | `log10` |
| `sin` | `sine` | `sin` |
| `sinh` | `hyperbolic_sine` | `sinh` |
| `sqrt` | `square_root` | `sqrt` |
| `tan` | `tangent` | `tan` |
| `tanh` | `hyperbolic_tangent` | `tanh` |

Applied to raw prices, most of these produce nothing useful. Arc cosine and arc sine are defined only between -1 and 1, so on INFY's prices, around 1,000 rupees, the `acos` and `asin` columns were entirely empty on 2026-09-14. `exponential`, `hyperbolic_cosine` and `hyperbolic_sine` overflow to infinity for any value above about 710; over ten years of INFY's adjusted closes, 1,586 of 1,654 rows were infinite. They are meant for columns that are already small, such as returns, passed through `column`.
