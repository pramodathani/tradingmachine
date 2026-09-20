# Funds and trusts

`tradingmachine.assets.funds` is two classes rather than six, because UBI carries no futures or options on a fund
or a trust and has no segment for them. Both of these trade on the exchange exactly as a share
does.

| Class | Base | Segment | Rows in UBI on 2026-09-20 |
| --- | --- | --- | --- |
| `ExchangeTradedFund` | `TradeableInstrument` | `exchange_traded_funds` | nse 353, bse 273 |
| `InvestmentTrust` | `TradeableInstrument` | `investment_trusts` | nse 27, bse 27 |

Both are named by exchange and symbol alone, with readable tickers such as `NIFTYBEES` for a fund
and `EMBASSY` for a trust. There is nothing to leave out and nothing written speculatively: unlike
the empty [currency index segments](currencies.md), the fund derivative segments do not exist in
UBI's vocabulary at all.

```python
from tradingmachine.assets import funds

fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
price = fund.last_price()
strength = fund.relative_strength_index(window=14, days=90)
row = fund.holdings

trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
level = trust.last_price()
```

## They behave like shares in every way that matters

Both are quoted continuously, both take the ordinary market and limit wrappers, and an order's
quantity is a plain count of units rather than the whole number of lots a commodity or currency
order needs. Both are also holdable, so both carry the same six holdings members `Equity` does,
and `cnc` is the right product for both.

A [mutual fund](mutual-funds.md) is a different thing and lives in its own module, because it is
subscribed to at its net asset value rather than traded.

## The one difference between the two classes

It is not in this module at all; it is in what UBI stores.

| | `ExchangeTradedFund` | `InvestmentTrust` |
| --- | --- | --- |
| Quoted | :material-check: yes | :material-check: yes |
| Orderable | :material-check: yes | :material-check: yes |
| Holdable | :material-check: yes | :material-check: yes |
| Candles | :material-check: adjusted, with a `price_factor` column | :material-close: none stored yet |
| Analysis methods | :material-check: return data | :material-close: nothing to work on |

`exchange_traded_funds` is one of UBI's adjustable segments, along with equities and investment
trusts, so a fund's candles come back adjusted for splits and bonuses. A trust's candles are not
stored at all yet, so `prices()` returns `None` for an `InvestmentTrust` and every inherited
analysis method has nothing to work on, even though the trust is quoted and traded normally.

The difference shows up most clearly in the analysis methods. Measured on 2026-09-20,
`relative_strength_index(window=14, days=90)` returned 63 rows for NSE `NIFTYBEES` and `None` for
NSE `EMBASSY`.

!!! note "The same fund on two exchanges is two instruments"

    `NIFTYBEES` is listed on both the nse and the bse, with a separate `instrument_id` and a
    separate price on each. On 2026-09-20 they were 266.53 and 266.6. That is the ordinary
    cross-listing difference rather than anything to reconcile.
