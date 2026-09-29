---
hide:
  - navigation
---

# Trading Machine

<div class="hero" markdown>

<p class="lead"><code>tradingmachine</code> is a Python library that turns Indian market instruments into <strong>objects you can ask questions of and trade through</strong>. You write <code>Equity("nse", "RELIANCE")</code>, and that object gives you its candles, its live quote, its order book, over 200 kinds of technical analysis and performance measures, its orders, its positions and its holdings. Instruments can also be gathered into baskets, such as a portfolio, a watchlist or an index, which are analysed the same way. Underneath, every question goes to the <a href="https://pramodathani.github.io/unified_broker_interface/">Unified Broker Interface</a> (UBI), which combines ten stock brokers into one account.</p>

</div>

<figure class="diagram">
--8<-- "docs/assets/diagrams/overview.svg"
<figcaption>Orange dots are quotes, candles, orders and positions coming up from the brokers, through the shared client, to the instrument objects and the asset baskets, and on to your program; the orange dot below the baskets is a basket being saved to or loaded from MongoDB. Blue dots are orders going the other way, from a synthetic order or a portfolio, through UBI to one broker.</figcaption>
</figure>

## Start here

The site is split into tabs along the top. Most readers want the first card, which lists every class and member of the library on one page.

<div class="grid cards" markdown>

-   :material-language-python:{ .lg .middle } **Python API**

    ---

    Every public member, one group per page, with parameters, examples captured from a real UBI, return values and exceptions.

    [:octicons-arrow-right-24: Go to the Python API](python-api/index.md)

-   :material-rocket-launch:{ .lg .middle } **Get started**

    ---

    Install the library, start its three databases, point it at UBI, and run a first session.

    [:octicons-arrow-right-24: Installation](get-started/index.md)

-   :material-shape:{ .lg .middle } **Asset classes**

    ---

    The 27 instrument classes across equities, fixed income, commodities, currencies, funds and mutual funds, and what each can and cannot do.

    [:octicons-arrow-right-24: Compare the families](asset-classes/index.md)

-   :material-chart-bell-curve-cumulative:{ .lg .middle } **Analysis**

    ---

    TA-Lib indicators, candlestick patterns, statistics, crossovers, a backtest and performance measures such as the Sharpe ratio, inherited by every instrument and every basket.

    [:octicons-arrow-right-24: Analyse candles](analysis/index.md)

-   :material-layers-triple:{ .lg .middle } **Architecture**

    ---

    The layers from your program down to the brokers, how UBI places orders, and why the library is built the way it is.

    [:octicons-arrow-right-24: How it fits together](architecture/index.md)

-   :material-folder-cog:{ .lg .middle } **Project**

    ---

    The repository's layout, how to add an asset class, and how this site is built and published.

    [:octicons-arrow-right-24: Work on the project](project/index.md)

</div>

## A first taste

The example below looks up one share and reads three things from it. The output was captured from a local UBI on Saturday 2026-09-26, so the prices are Friday's close, and the DataFrame is trimmed to its first two rows.

=== "Python"

    ```python
    from tradingmachine.assets import equities

    reliance = equities.Equity("nse", "RELIANCE")
    print(reliance.last_price)
    print(reliance.prices(days=10))
    print(equities.Equity.search("nse", "RELI", limit=5)["symbol"].tolist())
    ```

=== "Output"

    ```text
    1226.0
      exchange       segment interval                  datetime    open    high     low   close    volume    oi  price_factor
    0      nse  nse_equities      day 2026-09-16 00:00:00+05:30  1243.0  1255.0  1240.0  1240.0  10023997  None           1.0
    1      nse  nse_equities      day 2026-09-17 00:00:00+05:30  1244.8  1253.4  1238.5  1243.9   7752895  None           1.0
    ['RELIABLE', 'RELIANCE', 'RELIGARE', 'RELINFRA']
    ```

`last_price` has no brackets because it only reports a value, so it is a property. `prices` has brackets because it takes arguments, so it is a method. The whole library follows that rule.

## The library in numbers

The table below counts what the library holds today, so you can judge the size of each part before you read about it.

| What | Count | Where |
|---|---:|---|
| Instrument classes | 27 | `src/tradingmachine/assets/`, in six family modules |
| Kinds of asset basket | 5 | `src/tradingmachine/asset_baskets/`, one module each |
| Synthetic order classes | 53 | `src/tradingmachine/orders/`, one module each |
| Analysis methods inherited by every instrument and basket | 209 | `src/tradingmachine/assets/analysis/`, in fourteen classes |
| Price wrappers such as `buy_at_best_bid_price` | 32 | `TradeableInstrument` in `src/tradingmachine/assets/instruments.py` |
| Exception classes | 55 | 38 in `assets/exceptions.py`, 13 in `unified_broker_interface/exceptions.py`, 4 in `asset_baskets/exceptions.py` |
| Python modules | 103 | `src/tradingmachine/`, counting each package's `__init__.py` |

## What the library adds to UBI

UBI already answers every question the library asks, over HTTP. The comparison below shows what the library adds on top, using the same order written both ways.

=== "With tradingmachine"

    ```python
    from tradingmachine.assets import equities

    reliance = equities.Equity("nse", "RELIANCE")
    reliance.buy_at_best_bid_price(quantity=1, product="cnc")
    ```

=== "Calling UBI directly"

    ```python
    import requests

    base_url = "http://127.0.0.1:8080"
    session = requests.post(
        f"{base_url}/api/session/connect",
        headers={"api-key": API_KEY, "api-secret": API_SECRET},
    ).json()
    headers = {"access-token": session["access-token"]}
    details = requests.get(
        f"{base_url}/api/instruments/details",
        headers=headers,
        params={"exchange": "nse", "segment": "nse_equities", "symbol": "RELIANCE"},
    ).json()
    requests.post(
        f"{base_url}/api/orders/place",
        headers=headers,
        json={
            "instrument_id": details["instrument_id"],
            "transaction_type": "buy",
            "order_type": "limit",
            "product": "cnc",
            "after_market": False,
            "dry_run": False,
            "quantity": 1,
            "price_reference": {"kind": "bid_level", "level": 1},
        },
    )
    ```

The library looks the instrument up once, keeps the one shared login alive and renews it when UBI answers HTTP 401, and turns each error status into a named exception. It deliberately does not cache anything, round prices or check lot sizes, because UBI does all three.

!!! danger "Orders are real"
    Every member that places an order sends it through UBI to a real broker, with real money. The [Orders](python-api/orders.md) page explains `dry_run`, which asks UBI to check an order and show what it would send, without sending it.
