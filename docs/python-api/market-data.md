# Market data

These members read prices: the candles an instrument has traded in, its latest quote, and the order book behind that quote. Every instrument has the candles and the quote, and every tradeable instrument also has the order book, so an index has `last_price` but no `best_bid`.

The table below lists every member on this page. Only `prices` is a method, because it takes an interval and a range; everything else is a property, read like an attribute.

| Kind | Member | Description |
|---|---|---|
| <span class="member method">method</span> | [`prices`](#prices) | Candles for an interval and a date range, as a DataFrame |
| <span class="member property">property</span> | [`quote`](#quote) | The full unified quote, as a dict |
| <span class="member property">property</span> | [`last_price`](#last_price) | The last traded price, as a float |
| <span class="member property">property</span> | [`ohlc`](#ohlc) | The day's open, high and low with the last and previous close |
| <span class="member property">property</span> | [`bids`](#bids) | The buy side of the order book |
| <span class="member property">property</span> | [`asks`](#asks) | The sell side of the order book |
| <span class="member property">property</span> | [`best_bid`](#best_bid) | The highest bid |
| <span class="member property">property</span> | [`best_offer`](#best_offer) | The lowest offer |
| <span class="member property">property</span> | [`bid_offer_spread`](#bid_offer_spread) | The best offer minus the best bid, from one quote |
| <span class="member property">property</span> | [`mid_price`](#mid_price) | Halfway between the best bid and the best offer, from one quote |
| <span class="member property">property</span> | [`volume_weighted_average_price`](#volume_weighted_average_price) | Today's volume weighted average price |
| <span class="member property">property</span> | [`last_quantity`](#last_quantity) | The size of the last trade |
| <span class="member property">property</span> | [`total_traded_volume`](#total_traded_volume) | The quantity traded so far today |
| <span class="member property">property</span> | [`open_interest`](#open_interest) | The open interest of a future or an option |
| <span class="member property">property</span> | [`last_trade_time`](#last_trade_time) | When the last trade happened, in India time |

The strings `prices` accepts for `interval` are listed below. [Vocabulary](vocabulary.md#intervals) has them too, beside every other plain string the library passes through.

| Parameter | Values |
|---|---|
| `interval` | `day`, `1minute`, `2minute`, `3minute`, `4minute`, `5minute`, `10minute`, `15minute`, `20minute`, `25minute`, `30minute`, `45minute`, `60minute`, `120minute`, `180minute`, `240minute` |

## Every read goes to UBI

Nothing on this page is cached. Each read of a property sends one request to UBI and returns what UBI answered at that moment, and the next read sends another. UBI runs on the same machine and answers from its own Redis, so a read is cheap, but it is never free, and two reads of the same property can disagree because the market moved between them.

The animation below follows one read of `last_price` from your code to UBI and back.

<figure class="diagram">
--8<-- "docs/assets/diagrams/read-path.svg"
<figcaption>Orange dots carry the request out, and green dots carry UBI's answer back. Every read of a property makes this whole trip.</figcaption>
</figure>

!!! tip "Bind a value you need twice"
    `share.last_price` looks like an attribute, but it is a request. Code that uses the same value more than once should read it into a local variable first, both to save the request and to be sure the two uses see the same number.

The values that need two numbers from the same moment, `bid_offer_spread` and `mid_price`, read one quote and take both sides from it, rather than reading `best_bid` and `best_offer`, which would be two requests and could mix two moments.

## prices

<div class="endpoint" markdown><span class="member method">method</span> `prices(interval="day", from_date=None, to_date=None, days=None, adjusted=True)`<span class="route"><span class="method get">GET</span> `/api/instruments/prices`</span></div>

This method fetches the instrument's candles for one interval and one range, in a single request however long the range is. Give either `from_date` and `to_date`, or `days`. The answer is a pandas DataFrame sorted by time, with the time converted to India time, or `None` when UBI has no candles for the range.

#### Parameters

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `interval` | `str` | No | `"day"` | The candle length, one of the [intervals](vocabulary.md#intervals) in the table above |
| `from_date` | `datetime.date`, `str` or `None` | With `to_date` | `None` | The first day, inclusive, as a date or `YYYY-MM-DD` |
| `to_date` | `datetime.date`, `str` or `None` | With `from_date` | `None` | The last day, inclusive |
| `days` | `int` or `None` | Instead of the two dates | `None` | Count back this many days from today. UBI includes both ends, so `days=10` covers eleven calendar days. |
| `adjusted` | `bool` | No | `True` | `True` for prices adjusted for splits and bonuses, which adds a `price_factor` column |

#### Example

The output below was captured from a local UBI on Saturday 2026-09-26. The daily call returned six rows and the capture printed the first five, so the sixth row is not shown here. The five-minute call over the last day returned `None`, because UBI had no five-minute candles stored for that range.

=== "Python"

    ```python
    daily = reliance.prices(days=10)
    print(daily.shape)
    print(daily.head(5).to_string())

    intraday = reliance.prices(interval="5minute", days=1)
    print(intraday)
    ```

=== "Output"

    ```text
    (6, 11)
      exchange       segment interval                  datetime    open    high     low   close    volume    oi  price_factor
    0      nse  nse_equities      day 2026-09-16 00:00:00+05:30  1243.0  1255.0  1240.0  1240.0  10023997  None           1.0
    1      nse  nse_equities      day 2026-09-17 00:00:00+05:30  1244.8  1253.4  1238.5  1243.9   7752895  None           1.0
    2      nse  nse_equities      day 2026-09-18 00:00:00+05:30  1245.0  1247.3  1226.4  1226.4  15122715  None           1.0
    3      nse  nse_equities      day 2026-09-21 00:00:00+05:30  1234.1  1249.1  1232.5  1247.4  10007218  None           1.0
    4      nse  nse_equities      day 2026-09-22 00:00:00+05:30  1247.6  1251.9  1237.4  1240.4  10684376  None           1.0
    None
    ```

The chart below draws those five captured daily candles. A green body closed above its open and a red body closed below it, and the thin line runs from the day's low to its high.

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "RELIANCE daily candles on the nse from 2026-09-16 to 2026-09-22, captured from a local UBI on 2026-09-26.",
  "width": "container",
  "height": 260,
  "data": {
    "values": [
      {"day": "2026-09-16", "open": 1243.0, "high": 1255.0, "low": 1240.0, "close": 1240.0, "volume": 10023997},
      {"day": "2026-09-17", "open": 1244.8, "high": 1253.4, "low": 1238.5, "close": 1243.9, "volume": 7752895},
      {"day": "2026-09-18", "open": 1245.0, "high": 1247.3, "low": 1226.4, "close": 1226.4, "volume": 15122715},
      {"day": "2026-09-21", "open": 1234.1, "high": 1249.1, "low": 1232.5, "close": 1247.4, "volume": 10007218},
      {"day": "2026-09-22", "open": 1247.6, "high": 1251.9, "low": 1237.4, "close": 1240.4, "volume": 10684376}
    ]
  },
  "encoding": {
    "x": {"field": "day", "type": "ordinal", "title": "Day", "axis": {"labelAngle": 0}},
    "y": {"type": "quantitative", "scale": {"zero": false}, "title": "Price in rupees"},
    "color": {
      "condition": {"test": "datum.open <= datum.close", "value": "#1b8a3a"},
      "value": "#c62828"
    },
    "tooltip": [
      {"field": "day", "type": "ordinal", "title": "Day"},
      {"field": "open", "type": "quantitative", "title": "Open"},
      {"field": "high", "type": "quantitative", "title": "High"},
      {"field": "low", "type": "quantitative", "title": "Low"},
      {"field": "close", "type": "quantitative", "title": "Close"},
      {"field": "volume", "type": "quantitative", "title": "Volume", "format": ","}
    ]
  },
  "layer": [
    {
      "mark": "rule",
      "encoding": {
        "y": {"field": "low"},
        "y2": {"field": "high"}
      }
    },
    {
      "mark": {"type": "bar", "size": 18},
      "encoding": {
        "y": {"field": "open"},
        "y2": {"field": "close"}
      }
    }
  ]
}
```

#### Returns

A pandas DataFrame, or `None` when UBI has no candles for the range. The table below lists its columns, with the dtypes from the same capture.

| Column | Type | Description |
|---|---|---|
| `exchange` | `str` | The instrument's exchange, added by this library |
| `segment` | `str` | The instrument's segment, added by this library |
| `interval` | `str` | The interval asked for, added by this library |
| `datetime` | `datetime64[us, Asia/Kolkata]` | The candle's start in India time. UBI calls this column `time` and sends it in UTC; the library renames and converts it, so a daily candle reads midnight India time rather than 18:30 the day before. |
| `open` | `float64` | The first price in the candle |
| `high` | `float64` | The highest price |
| `low` | `float64` | The lowest price |
| `close` | `float64` | The last price |
| `volume` | `int64` | The quantity traded, in underlying units |
| `oi` | `object` | Open interest for a future or an option, or `None` |
| `price_factor` | `float64` | The adjustment factor applied, present only when `adjusted=True` |

#### Raises

| Exception | When |
|---|---|
| [`BadRequestError`](errors.md#badrequesterror) | The range or interval is invalid, such as both `days` and `from_date`, or an intraday range longer than 366 days |
| [`UnifiedBrokerInterfaceError`](errors.md#unifiedbrokerinterfaceerror) | Any other failure reported by, or on the way to, UBI |

Some families have no candles at all, so `prices` returns `None` for every bond, currency pair, investment trust and mutual fund. [Asset classes](../asset-classes/index.md) lists which classes have candles.

??? note "Under the hood"
    The request carries `instrument_id`, `interval`, `adjusted` as the text `true` or `false`, and whichever of `from`, `to` and `days` were given. UBI answers with a `columns` list and a `candles` list of rows. See [Prices](https://pramodathani.github.io/unified_broker_interface/rest-api/historical-data/#prices) on the UBI site for the route, including where the candles come from and how adjustment works.

## quote

<div class="endpoint" markdown><span class="member property">property</span> `quote`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the instrument's full unified quote, which is UBI's merged view of the latest price, the day's figures and five levels of the order book. It is the source every order-book property below reads from.

#### Parameters

This property takes no parameters.

#### Example

The output below was captured from a local UBI on Saturday 2026-09-26, so it holds Friday's closing figures. Note that `depth.buy` is empty: nobody was bidding in the book the broker last reported.

=== "Python"

    ```python
    print(reliance.quote)
    ```

=== "Output"

    ```text
    {'average_price': 1220.44, 'broker': 'zerodha', 'broker_token': '738561', 'buy_quantity': 0, 'change_percent': 0.5577, 'depth': {'buy': [], 'sell': [{'orders': 11, 'price': 1226.0, 'quantity': 855}]}, 'exchange': 'nse', 'exchange_time': 1790332198.0, 'expiry_date': None, 'instrument_id': '3f92570a-9924-5bf5-9f9d-e006cd9f4202', 'last_price': 1226.0, 'last_quantity': 1, 'last_trade_time': 1790332190.0, 'lot_size': 1, 'ohlc': {'high': 1227.4, 'low': 1210.5, 'open': 1210.5}, 'oi': None, 'oi_day_high': None, 'oi_day_low': None, 'option_type': None, 'previous_close': 1219.2, 'received_at': 1790332199.1126616, 'segment': 'nse_equities', 'shape': 'security', 'source': 'cache', 'stale': False, 'stale_since': None, 'strike_price': None, 'symbol': 'RELIANCE', 'underlying_symbol': None, 'unified_at': 1790332199.1187558, 'volume': 13138735}
    ```

#### Returns

A `dict` holding UBI's unified quote. The fields that matter most are `last_price`, `average_price`, `ohlc`, `previous_close`, `change_percent`, `volume`, `oi` and `depth`; `broker` names the broker the quote came from, and `source` says whether UBI answered from its cache (`cache`) or asked a broker while you waited (`broker`). [The unified quote document](https://pramodathani.github.io/unified_broker_interface/rest-api/market-quotes/#the-unified-quote-document) on the UBI site describes every field.

#### Raises

| Exception | When |
|---|---|
| [`ServiceUnavailableError`](errors.md#serviceunavailableerror) | UBI has no recent quote and no broker could supply one, which is always the case for a cash bond, a fixed income index and a mutual fund |
| [`UnifiedBrokerInterfaceError`](errors.md#unifiedbrokerinterfaceerror) | Any other failure reported by, or on the way to, UBI |

## last_price

<div class="endpoint" markdown><span class="member property">property</span> `last_price`<span class="route"><span class="method get">GET</span> `/api/instruments/ltp`</span></div>

This property returns the last traded price in rupees. It uses UBI's smaller `ltp` route rather than the full quote, and it works on indices as well as on tradeable instruments.

#### Parameters

This property takes no parameters.

#### Example

The output below was captured from a local UBI on 2026-09-26, for RELIANCE and for the first MCX gold future.

=== "Python"

    ```python
    from tradingmachine.assets import commodities

    print(reliance.last_price)

    expiries = commodities.CommodityFutures.expiries("mcx", "GOLD")
    gold = commodities.CommodityFutures("mcx", "GOLD", expiries[0])
    print(gold.last_price)
    ```

=== "Output"

    ```text
    1226.0
    150734.0
    ```

#### Returns

A `float`, or `None` when UBI has no last price for the instrument.

#### Raises

| Exception | When |
|---|---|
| [`ServiceUnavailableError`](errors.md#serviceunavailableerror) | UBI has no recent quote and no broker could supply one |
| [`UnifiedBrokerInterfaceError`](errors.md#unifiedbrokerinterfaceerror) | Any other failure reported by, or on the way to, UBI |

## ohlc

<div class="endpoint" markdown><span class="member property">property</span> `ohlc`<span class="route"><span class="method get">GET</span> `/api/instruments/ohlc`</span></div>

This property returns the day's open, high and low, with the last price and the previous close beside them. The inner `ohlc` dictionary has no close, because the day's close is the last price until the market shuts, so read `last_price` or `previous_close` from the outer dictionary instead.

#### Parameters

This property takes no parameters.

#### Example

The output below was captured from a local UBI on 2026-09-26.

=== "Python"

    ```python
    print(reliance.ohlc)
    ```

=== "Output"

    ```text
    {'change_percent': 0.5577, 'exchange': 'nse', 'expiry_date': None, 'instrument_id': '3f92570a-9924-5bf5-9f9d-e006cd9f4202', 'last_price': 1226.0, 'last_trade_time': 1790332190.0, 'ohlc': {'high': 1227.4, 'low': 1210.5, 'open': 1210.5}, 'option_type': None, 'previous_close': 1219.2, 'received_at': 1790332199.1126616, 'segment': 'nse_equities', 'shape': 'security', 'source': 'cache', 'strike_price': None, 'symbol': 'RELIANCE', 'underlying_symbol': None}
    ```

#### Returns

A `dict` with `last_price`, `ohlc` (itself a dict of `open`, `high` and `low`), `previous_close`, `change_percent`, `last_trade_time`, `received_at`, `source` and the instrument's identity fields. On an index the inner values can all be `None`; a check on 2026-09-22 before the open read `{'high': None, 'low': None, 'open': None}` for NIFTY.

#### Raises

| Exception | When |
|---|---|
| [`ServiceUnavailableError`](errors.md#serviceunavailableerror) | UBI has no recent quote and no broker could supply one |
| [`UnifiedBrokerInterfaceError`](errors.md#unifiedbrokerinterfaceerror) | Any other failure reported by, or on the way to, UBI |

## The order book values

The eleven properties in this section belong to `TradeableInstrument`, so every class except the four index classes has them. Each one reads the [`quote`](#quote) once and takes one part of it, which means each read is one request to `GET /api/instruments/quote`. None of them takes a parameter, and each raises [`UnifiedBrokerInterfaceError`](errors.md#unifiedbrokerinterfaceerror) or one of its subclasses when the quote cannot be read.

The table below shows where each property comes from in the quote, and what the capture on Saturday 2026-09-26 returned for RELIANCE.

| Property | Read from the quote | RELIANCE on 2026-09-26 |
|---|---|---|
| `bids` | `depth.buy` | `[]` |
| `asks` | `depth.sell` | `[{'orders': 11, 'price': 1226.0, 'quantity': 855}]` |
| `best_bid` | the first of `depth.buy` | `None` |
| `best_offer` | the first of `depth.sell` | `{'orders': 11, 'price': 1226.0, 'quantity': 855}` |
| `bid_offer_spread` | both sides of one quote | `None` |
| `mid_price` | both sides of one quote | `None` |
| `volume_weighted_average_price` | `average_price` | `1220.44` |
| `last_quantity` | `last_quantity` | `1`, read from the quote itself because the property was not captured on its own |
| `total_traded_volume` | `volume` | `13138735` |
| `open_interest` | `oi` | `None`, read from the quote itself; a share has no open interest |
| `last_trade_time` | `last_trade_time` | `datetime.datetime(2026, 9, 25, 15, 59, 50, tzinfo=zoneinfo.ZoneInfo(key='Asia/Kolkata'))` |

!!! warning "An empty side makes three values `None`"
    The capture was taken on a Saturday, when the book the broker last reported had sellers but no buyers. With `bids` empty, `best_bid` is `None`, and so are `bid_offer_spread` and `mid_price`, because both need a best bid. Code that does arithmetic on these values must check for `None` first. The opposite surprise is possible too: a check before the open on 2026-09-22 found a crossed book, with the best bid 207.6 above the best offer, and `bid_offer_spread` returned `-207.6`, because neither property checks the book for sense.

### bids

<div class="endpoint" markdown><span class="member property">property</span> `bids`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the buy side of the order book, best price first. It is a `list` of up to five dicts, each with `price`, `quantity` and `orders`, and it is empty when nobody is bidding.

#### Example

The output below was captured from a local UBI on 2026-09-26.

=== "Python"

    ```python
    print(reliance.bids)
    ```

=== "Output"

    ```text
    []
    ```

### asks

<div class="endpoint" markdown><span class="member property">property</span> `asks`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the sell side of the order book, best price first. It is a `list` of up to five dicts, each with `price`, `quantity` and `orders`, and it is empty when nobody is offering.

#### Example

The output below was captured from a local UBI on 2026-09-26.

=== "Python"

    ```python
    print(reliance.asks)
    ```

=== "Output"

    ```text
    [{'orders': 11, 'price': 1226.0, 'quantity': 855}]
    ```

### best_bid

<div class="endpoint" markdown><span class="member property">property</span> `best_bid`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the highest bid as a `dict` with `price`, `quantity` and `orders`, or `None` when nobody is bidding.

#### Example

The output below was captured from a local UBI on 2026-09-26, when the bid side was empty.

=== "Python"

    ```python
    print(reliance.best_bid)
    ```

=== "Output"

    ```text
    None
    ```

### best_offer

<div class="endpoint" markdown><span class="member property">property</span> `best_offer`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the lowest offer as a `dict` with `price`, `quantity` and `orders`, or `None` when nobody is offering.

#### Example

The output below was captured from a local UBI on 2026-09-26.

=== "Python"

    ```python
    print(reliance.best_offer)
    ```

=== "Output"

    ```text
    {'orders': 11, 'price': 1226.0, 'quantity': 855}
    ```

### bid_offer_spread

<div class="endpoint" markdown><span class="member property">property</span> `bid_offer_spread`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the best offer's price minus the best bid's price, in rupees, both taken from one quote. It is a `float`, or `None` when either side of the book is empty, and it can be negative when the book is crossed.

#### Example

The output below was captured from a local UBI on 2026-09-26, when the bid side was empty.

=== "Python"

    ```python
    print(reliance.bid_offer_spread)
    ```

=== "Output"

    ```text
    None
    ```

### mid_price

<div class="endpoint" markdown><span class="member property">property</span> `mid_price`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the price halfway between the best bid and the best offer, both taken from one quote. It is a `float` in rupees, or `None` when either side of the book is empty.

#### Example

The output below was captured from a local UBI on 2026-09-26, when the bid side was empty.

=== "Python"

    ```python
    print(reliance.mid_price)
    ```

=== "Output"

    ```text
    None
    ```

### volume_weighted_average_price

<div class="endpoint" markdown><span class="member property">property</span> `volume_weighted_average_price`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns today's volume weighted average price, which is the quote's `average_price`. It is a `float` in rupees, or `None` when the broker serving the quote does not report it, as happened for INFY before the open on 2026-09-22.

#### Example

The output below was captured from a local UBI on 2026-09-26.

=== "Python"

    ```python
    print(reliance.volume_weighted_average_price)
    ```

=== "Output"

    ```text
    1220.44
    ```

### last_quantity

<div class="endpoint" markdown><span class="member property">property</span> `last_quantity`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the size of the last trade as an `int` in underlying units, not lots, or `None` when it is unknown. The captured quote above shows `'last_quantity': 1` for RELIANCE; the property itself was not read separately in that capture.

### total_traded_volume

<div class="endpoint" markdown><span class="member property">property</span> `total_traded_volume`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the quantity traded so far today, which is the quote's `volume`. It is an `int` in underlying units, not lots, or `None` when it is unknown.

#### Example

The output below was captured from a local UBI on 2026-09-26.

=== "Python"

    ```python
    print(reliance.total_traded_volume)
    ```

=== "Output"

    ```text
    13138735
    ```

### open_interest

<div class="endpoint" markdown><span class="member property">property</span> `open_interest`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns the open interest of a future or an option, which is the quote's `oi`. It is an `int` in underlying units, or `None` for a security or when it is unknown. The captured quote above shows `'oi': None` for RELIANCE, as expected for a share; the property itself was not read separately in that capture.

### last_trade_time

<div class="endpoint" markdown><span class="member property">property</span> `last_trade_time`<span class="route"><span class="method get">GET</span> `/api/instruments/quote`</span></div>

This property returns when the last trade happened, as a timezone-aware `datetime.datetime` in India time. UBI sends it as seconds since the epoch, and the property converts it. It is `None` when the broker does not send the time reliably.

#### Example

The output below was captured from a local UBI on Saturday 2026-09-26, so the last trade is Friday's. The quote's raw value was `1790332190.0`.

=== "Python"

    ```python
    print(repr(reliance.last_trade_time))
    ```

=== "Output"

    ```text
    datetime.datetime(2026, 9, 25, 15, 59, 50, tzinfo=zoneinfo.ZoneInfo(key='Asia/Kolkata'))
    ```

??? note "Under the hood"
    `bids`, `asks`, `volume_weighted_average_price`, `last_quantity`, `total_traded_volume`, `open_interest` and `last_trade_time` each read `self.quote` once. `best_bid` and `best_offer` read `bids` or `asks`, which is still one quote. `bid_offer_spread` and `mid_price` read `self.quote["depth"]` once and take both sides from it. UBI already drops empty levels from the depth, so the library does no filtering of its own. See [Quote](https://pramodathani.github.io/unified_broker_interface/rest-api/market-quotes/#quote) on the UBI site for the route and [Where a quote comes from](https://pramodathani.github.io/unified_broker_interface/rest-api/market-quotes/#where-a-quote-comes-from) for how UBI chooses between its cache and a broker.
