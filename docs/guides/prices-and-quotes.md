# Candles and quotes

Every instrument, tradeable or not, can be asked for its candle history and its live prices. A
tradeable one can also be asked about the order book.

## Candles

`prices` fetches a range of candles as a `pandas.DataFrame`. You give it either a pair of dates or
a number of days to count back, and UBI serves any range in one request.

```python
from tradingmachine.assets import equities

share = equities.Equity(exchange="nse", symbol="RELIANCE")

year = share.prices(days=365)
window = share.prices(from_date="2026-01-01", to_date="2026-03-31")
intraday = share.prices(interval="5minute", days=5)
raw = share.prices(days=365, adjusted=False)
```

| Argument | Default | What it does |
| --- | --- | --- |
| `interval` | `"day"` | The candle interval, such as `day` or `5minute` |
| `from_date`, `to_date` | `None` | The ends of the range, as a `datetime.date` or a `YYYY-MM-DD` string |
| `days` | `None` | Count back this many days from today, instead of giving dates |
| `adjusted` | `True` | Adjust for splits and bonuses |

Give dates or `days`, not both; UBI answers HTTP 400 when both arrive.

The frame comes back sorted by time, with a fresh index.

| Column | What it is |
| --- | --- |
| `exchange`, `segment`, `interval` | Inserted here, so several frames can be concatenated without losing track |
| `datetime` | Timezone-aware, converted to `Asia/Kolkata` |
| `open`, `high`, `low`, `close` | The candle, in rupees |
| `volume`, `oi` | Traded volume and open interest |
| `price_factor` | Only when `adjusted=True`, and only where UBI adjusts the segment |

!!! warning "`None` means there is nothing, and that is common"

    `prices` returns `None` rather than an empty frame when UBI has no candles for the range. For
    whole families that is the permanent answer: nothing in
    [fixed income](../asset-classes/fixed-income.md) or
    [currencies](../asset-classes/currencies.md) has candles at all, and neither does an
    [investment trust](../asset-classes/funds.md) or a
    [mutual fund](../asset-classes/mutual-funds.md). Check for `None` before indexing into the
    result.

## Live prices

Three properties ask about the present rather than the past, and they differ in how much they
fetch. Each one sends its own request to UBI every time it is read, so it is a live reading rather
than a stored value.

| Property | Returns | Use it for |
| --- | --- | --- |
| `last_price` | A `float`, or `None` | The one number, at the lowest cost |
| `ohlc` | A `dict` | The day's open, high and low with the last and previous close and the change |
| `quote` | A `dict` | Everything, including the order book under `depth` |

```python
price = share.last_price

day = share.ohlc
day["ohlc"]["open"], day["previous_close"], day["change_percent"]

full = share.quote
full["volume"], full["oi"], full["depth"]
```

Each of the three sends its own request. There is no cache between them, so reading `last_price`
three times sends three requests. UBI is local and caches in its own Redis, which is what makes
that acceptable.

!!! note "`ServiceUnavailableError` is the normal answer for some instruments"

    A cash bond, a rate index, a commodity, a currency pair and a mutual fund have no quote at all,
    so all three of these properties raise `ServiceUnavailableError` rather than returning `None`.
    That
    is UBI reporting that no broker that serves quotes carries the instrument, not a fault. The
    [coverage table](../asset-classes/index.md#what-ubi-actually-carries) says which is which.

## The order book

`TradeableInstrument` adds the values that come out of the quote's `depth`. They are properties
too, and each one sends its own `quote` request when it is read.

| Property | Returns |
| --- | --- |
| `bids`, `asks` | Up to five `dict` levels with `price`, `quantity` and `orders`, best first |
| `best_bid`, `best_offer` | The first level of each side, or `None` when that side is empty |
| `bid_offer_spread` | Best offer minus best bid, or `None` when either side is empty |
| `mid_price` | The midpoint of the two, or `None` |
| `volume_weighted_average_price` | The day's volume-weighted average |
| `last_quantity`, `total_traded_volume`, `open_interest` | The traded figures |
| `last_trade_time` | A timezone-aware `datetime`, or `None` |

```python
if share.best_bid is not None:
    print(share.best_bid["price"], share.bid_offer_spread)
```

The price-named order wrappers price their orders from this same book, but they do not read it
here. They describe the level they want and UBI reads the book itself when it sends the order, so
an empty side comes back from UBI as `ServiceUnavailableError`. See [Orders](orders.md).
