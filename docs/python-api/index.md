# Python API

This tab documents every public class and member of the `tradingmachine` library, laid out like Zerodha's Kite Connect documentation: each page opens with a summary table, then gives each member its own section with its parameters, an example, what it returns and what it raises. This page is the index of all of them, one table per page, so you can find any member in one scroll.

The library is a Python face on the [Unified Broker Interface](https://pramodathani.github.io/unified_broker_interface/) (UBI), a REST API that combines ten Indian stock brokers into one account. Almost every member here sends one request to UBI, and each member's section names the UBI route it calls.

## How to read the badges

Every member carries a coloured badge saying what kind of thing it is. The badge matters most for the red one, because those members send real orders to real brokers.

| Badge | Meaning |
|---|---|
| <span class="member property">property</span> | Reads a value from UBI each time you access it, and never writes anything. Written without brackets: `instrument.last_price`. |
| <span class="member method">method</span> | Takes arguments and reads only. Written with brackets: `instrument.prices(days=10)`. |
| <span class="member function">classmethod</span> | Called on the class rather than on an instrument, to find instruments: `Equity.search("nse", "RELI")`. |
| <span class="member writes">places orders</span> | Sends orders to a broker, or cancels or changes them. These act on real money. |
| <span class="member class">class</span> | A class you construct. |

The rule behind the first two badges is the library's own: anything that only reports a value is a property, and only members that take an argument or write to the market are methods.

## Where the members are

The chart below counts the members documented on each page of this tab, which shows where the bulk of the library's surface is. The 32 price wrappers are the largest group, because each names one place a price can come from.

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Number of public members documented on each Python API page",
  "width": "container",
  "height": 260,
  "data": {
    "values": [
      {"page": "Price wrappers", "members": 32},
      {"page": "Market data", "members": 15},
      {"page": "Orders", "members": 10},
      {"page": "Positions", "members": 8},
      {"page": "The UBI client", "members": 8},
      {"page": "Holdings", "members": 6},
      {"page": "Finding instruments", "members": 5},
      {"page": "Instruments", "members": 1},
      {"page": "The account", "members": 1}
    ]
  },
  "mark": {"type": "bar", "cornerRadiusEnd": 3, "color": "#ff7043"},
  "encoding": {
    "y": {"field": "page", "type": "nominal", "sort": "-x", "title": null},
    "x": {"field": "members", "type": "quantitative", "title": "Public members"},
    "tooltip": [{"field": "page"}, {"field": "members"}]
  }
}
```

Two pages hold classes rather than members. [Synthetic orders](synthetic-orders.md) documents the 42 order classes in `tradingmachine.orders`, and [Instruments](instruments.md) documents the 27 instrument classes. The thirteen classes of candle analysis, about 190 methods, have their own [Analysis](../analysis/index.md) tab.

## Instruments

An instrument is looked up once when you construct it, and from then on every member reads from UBI. The [Instruments](instruments.md) page documents the 27 classes, such as `Equity("nse", "RELIANCE")` or `EquityIndexOption("nse", "NIFTY", "2026-09-29", 25000, "CE")`, and the attributes the lookup fills in. The one member below belongs to every instrument class.

| Kind | Member | Description |
|---|---|---|
| <span class="member function">classmethod</span> | [`shared_unified_broker_interface`](instruments.md#shared_unified_broker_interface) | Returns the one client all instruments share, creating it on first use. |

## Market data

These members read candles, quotes and the order book. The first four work on every instrument; the order-book values exist only on instruments that can be traded, because an index has no order book.

| Kind | Member | Description |
|---|---|---|
| <span class="member method">method</span> | [`prices`](market-data.md#prices) | Fetches the instrument's candles for a range from UBI. |
| <span class="member property">property</span> | [`quote`](market-data.md#quote) | The instrument's full unified quote, read from UBI on every access. |
| <span class="member property">property</span> | [`last_price`](market-data.md#last_price) | The instrument's last traded price, read from UBI on every access. |
| <span class="member property">property</span> | [`ohlc`](market-data.md#ohlc) | The day's open, high and low with the last and previous close prices, read from UBI on every access. |
| <span class="member property">property</span> | [`bids`](market-data.md#bids) | The buy side of the order book, read from UBI on every access. |
| <span class="member property">property</span> | [`asks`](market-data.md#asks) | The sell side of the order book, read from UBI on every access. |
| <span class="member property">property</span> | [`best_bid`](market-data.md#best_bid) | The highest bid in the order book. |
| <span class="member property">property</span> | [`best_offer`](market-data.md#best_offer) | The lowest offer in the order book. |
| <span class="member property">property</span> | [`bid_offer_spread`](market-data.md#bid_offer_spread) | The gap between the best offer and the best bid, measured from one quote. |
| <span class="member property">property</span> | [`mid_price`](market-data.md#mid_price) | The price halfway between the best bid and the best offer, from one quote. |
| <span class="member property">property</span> | [`volume_weighted_average_price`](market-data.md#volume_weighted_average_price) | Today's volume weighted average price. |
| <span class="member property">property</span> | [`last_quantity`](market-data.md#last_quantity) | The quantity of the last trade. |
| <span class="member property">property</span> | [`total_traded_volume`](market-data.md#total_traded_volume) | The quantity traded so far today. |
| <span class="member property">property</span> | [`open_interest`](market-data.md#open_interest) | The open interest of a future or an option. |
| <span class="member property">property</span> | [`last_trade_time`](market-data.md#last_trade_time) | When the last trade happened. |

## Finding instruments

These class methods find instruments rather than read one. `search` exists on `Equity` and `EquityIndex`, and the other four on the derivative classes, each supplying its own segment.

| Kind | Member | Description |
|---|---|---|
| <span class="member function">classmethod</span> | [`search`](discovery.md#search) | Finds listed instruments whose symbol contains a term, on `Equity` and `EquityIndex`. |
| <span class="member function">classmethod</span> | [`expiries`](discovery.md#expiries) | Lists the expiry dates a derivative is listed for. |
| <span class="member function">classmethod</span> | [`contracts`](discovery.md#contracts) | Lists the contracts on an underlying as a DataFrame of identities. |
| <span class="member function">classmethod</span> | [`strikes`](discovery.md#strikes) | Lists the strike prices listed on one underlying for one expiry. |
| <span class="member function">classmethod</span> | [`chain`](discovery.md#chain) | Lists every option listed on one underlying for one expiry. |

## Orders

!!! danger "The red badges place real orders"
    Members with a <span class="member writes">places orders</span> badge send orders through UBI to real brokers, with real money. Pass `dry_run=True` to `place_order`, `modify_order` or `cancel_order` to have UBI check an order and show the request it would send, without sending it.

These members place, change and cancel orders in one instrument, and read that instrument's rows out of the day's order book and trade book.

| Kind | Member | Description |
|---|---|---|
| <span class="member writes">places orders</span> | [`place_order`](orders.md#place_order) | Places one order in this instrument through UBI. |
| <span class="member writes">places orders</span> | [`modify_order`](orders.md#modify_order) | Changes one pending order through UBI. |
| <span class="member writes">places orders</span> | [`cancel_order`](orders.md#cancel_order) | Cancels one pending order through UBI. |
| <span class="member writes">places orders</span> | [`cancel_open_orders`](orders.md#cancel_open_orders) | Cancels every order in this instrument that is still waiting in the market. |
| <span class="member property">property</span> | [`orders`](orders.md#orders) | Every one of today's orders in this instrument, whatever its status. |
| <span class="member property">property</span> | [`open_orders`](orders.md#open_orders) | Today's orders in this instrument that can still be changed. |
| <span class="member property">property</span> | [`completed_orders`](orders.md#completed_orders) | Today's orders in this instrument that filled in full. |
| <span class="member property">property</span> | [`rejected_orders`](orders.md#rejected_orders) | Today's orders in this instrument that a broker or the exchange refused. |
| <span class="member property">property</span> | [`cancelled_orders`](orders.md#cancelled_orders) | Today's orders in this instrument that were cancelled. |
| <span class="member property">property</span> | [`trades`](orders.md#trades) | Today's trades in this instrument. |

## Price wrappers

Each wrapper is `place_order` with the price source written into its name, so `buy_at_best_bid_price(quantity=1, product="cnc")` joins the queue at the best bid. Apart from the market and limit pairs, UBI works out the price itself when it sends the order. The twelve wrappers below name a single price.

| Kind | Member | Description |
|---|---|---|
| <span class="member writes">places orders</span> | [`buy_at_market_price`](price-wrappers.md#buy_at_market_price) | Buys at whatever price the market is asking. |
| <span class="member writes">places orders</span> | [`sell_at_market_price`](price-wrappers.md#sell_at_market_price) | Sells at whatever price the market is bidding. |
| <span class="member writes">places orders</span> | [`buy_at_limit_price`](price-wrappers.md#buy_at_limit_price) | Buys at a price of your choosing, or better. |
| <span class="member writes">places orders</span> | [`sell_at_limit_price`](price-wrappers.md#sell_at_limit_price) | Sells at a price of your choosing, or better. |
| <span class="member writes">places orders</span> | [`buy_at_best_bid_price`](price-wrappers.md#buy_at_best_bid_price) | Buys patiently, joining the queue at the highest price anyone is bidding. |
| <span class="member writes">places orders</span> | [`buy_at_best_offer_price`](price-wrappers.md#buy_at_best_offer_price) | Buys at once, by crossing the spread to the lowest price anyone is offering. |
| <span class="member writes">places orders</span> | [`sell_at_best_offer_price`](price-wrappers.md#sell_at_best_offer_price) | Sells patiently, joining the queue at the lowest price anyone is offering. |
| <span class="member writes">places orders</span> | [`sell_at_best_bid_price`](price-wrappers.md#sell_at_best_bid_price) | Sells at once, by crossing the spread to the highest price anyone is bidding. |
| <span class="member writes">places orders</span> | [`buy_at_mid_price`](price-wrappers.md#buy_at_mid_price) | Buys halfway between the best bid and the best offer. |
| <span class="member writes">places orders</span> | [`sell_at_mid_price`](price-wrappers.md#sell_at_mid_price) | Sells halfway between the best bid and the best offer. |
| <span class="member writes">places orders</span> | [`buy_at_volume_weighted_average_price`](price-wrappers.md#buy_at_volume_weighted_average_price) | Buys at the average price the day has traded at so far. |
| <span class="member writes">places orders</span> | [`sell_at_volume_weighted_average_price`](price-wrappers.md#sell_at_volume_weighted_average_price) | Sells at the average price the day has traded at so far. |
| <span class="member writes">places orders</span> | [`buy_at_marketable_price`](price-wrappers.md#buy_at_marketable_price) | Buys now with a limit order priced at the best offer, the price it takes to fill immediately. |
| <span class="member writes">places orders</span> | [`sell_at_marketable_price`](price-wrappers.md#sell_at_marketable_price) | Sells now with a limit order priced at the best bid, the price it takes to fill immediately. |
| <span class="member writes">places orders</span> | [`buy_at_last_price`](price-wrappers.md#buy_at_last_price) | Buys with a limit order at the price the instrument last traded at. |
| <span class="member writes">places orders</span> | [`sell_at_last_price`](price-wrappers.md#sell_at_last_price) | Sells with a limit order at the price the instrument last traded at. |

The other twenty reach deeper into the order book, from the second to the fifth price on each side. They are listed in the collapsed table below.

??? note "The twenty depth-level wrappers"

    | Kind | Member | Description |
    |---|---|---|
    | <span class="member writes">places orders</span> | [`buy_at_second_best_bid_price`](price-wrappers.md#buy_at_second_best_bid_price) | Buys at the second best price on the buy side of the book. |
    | <span class="member writes">places orders</span> | [`buy_at_third_best_bid_price`](price-wrappers.md#buy_at_third_best_bid_price) | Buys at the third best price on the buy side of the book. |
    | <span class="member writes">places orders</span> | [`buy_at_fourth_best_bid_price`](price-wrappers.md#buy_at_fourth_best_bid_price) | Buys at the fourth best price on the buy side of the book. |
    | <span class="member writes">places orders</span> | [`buy_at_fifth_best_bid_price`](price-wrappers.md#buy_at_fifth_best_bid_price) | Buys at the fifth best price on the buy side of the book. |
    | <span class="member writes">places orders</span> | [`sell_at_second_best_bid_price`](price-wrappers.md#sell_at_second_best_bid_price) | Sells at the second best price on the buy side of the book. |
    | <span class="member writes">places orders</span> | [`sell_at_third_best_bid_price`](price-wrappers.md#sell_at_third_best_bid_price) | Sells at the third best price on the buy side of the book. |
    | <span class="member writes">places orders</span> | [`sell_at_fourth_best_bid_price`](price-wrappers.md#sell_at_fourth_best_bid_price) | Sells at the fourth best price on the buy side of the book. |
    | <span class="member writes">places orders</span> | [`sell_at_fifth_best_bid_price`](price-wrappers.md#sell_at_fifth_best_bid_price) | Sells at the fifth best price on the buy side of the book. |
    | <span class="member writes">places orders</span> | [`buy_at_second_best_offer_price`](price-wrappers.md#buy_at_second_best_offer_price) | Buys at the second best price on the sell side of the book. |
    | <span class="member writes">places orders</span> | [`buy_at_third_best_offer_price`](price-wrappers.md#buy_at_third_best_offer_price) | Buys at the third best price on the sell side of the book. |
    | <span class="member writes">places orders</span> | [`buy_at_fourth_best_offer_price`](price-wrappers.md#buy_at_fourth_best_offer_price) | Buys at the fourth best price on the sell side of the book. |
    | <span class="member writes">places orders</span> | [`buy_at_fifth_best_offer_price`](price-wrappers.md#buy_at_fifth_best_offer_price) | Buys at the fifth best price on the sell side of the book. |
    | <span class="member writes">places orders</span> | [`sell_at_second_best_offer_price`](price-wrappers.md#sell_at_second_best_offer_price) | Sells at the second best price on the sell side of the book. |
    | <span class="member writes">places orders</span> | [`sell_at_third_best_offer_price`](price-wrappers.md#sell_at_third_best_offer_price) | Sells at the third best price on the sell side of the book. |
    | <span class="member writes">places orders</span> | [`sell_at_fourth_best_offer_price`](price-wrappers.md#sell_at_fourth_best_offer_price) | Sells at the fourth best price on the sell side of the book. |
    | <span class="member writes">places orders</span> | [`sell_at_fifth_best_offer_price`](price-wrappers.md#sell_at_fifth_best_offer_price) | Sells at the fifth best price on the sell side of the book. |

## Positions

These members act on this instrument's positions without being told which side you are on, so a long position is reduced by selling and a short one by buying.

| Kind | Member | Description |
|---|---|---|
| <span class="member property">property</span> | [`net_positions`](positions.md#net_positions) | The positions held in this instrument now, merged across every broker. |
| <span class="member property">property</span> | [`day_positions`](positions.md#day_positions) | Today's own positions in this instrument, without what was carried in. |
| <span class="member property">property</span> | [`positions_value`](positions.md#positions_value) | What this instrument's open positions are worth at the moment. |
| <span class="member property">property</span> | [`positions_pnl`](positions.md#positions_pnl) | What this instrument's positions have made or lost. |
| <span class="member writes">places orders</span> | [`add_to_position`](positions.md#add_to_position) | Makes an existing position bigger, or opens a new one. |
| <span class="member writes">places orders</span> | [`reduce_position`](positions.md#reduce_position) | Makes an existing position smaller, without turning it around. |
| <span class="member writes">places orders</span> | [`liquidate_position`](positions.md#liquidate_position) | Closes one position in this instrument completely. |
| <span class="member writes">places orders</span> | [`liquidate_all_positions`](positions.md#liquidate_all_positions) | Closes every position this instrument holds, under every product. |

## Holdings

Holdings are shares kept for the long term in a demat account. Only `Equity`, `FixedIncome`, `ExchangeTradedFund`, `InvestmentTrust` and `MutualFund` carry these six members, and their orders are always sent under the `cnc` product.

| Kind | Member | Description |
|---|---|---|
| <span class="member property">property</span> | [`holdings`](holdings.md#holdings) | The long-term holding of this share, merged across every broker. |
| <span class="member property">property</span> | [`holdings_value`](holdings.md#holdings_value) | What the shares held are worth at the moment. |
| <span class="member property">property</span> | [`holdings_pnl`](holdings.md#holdings_pnl) | What the shares held have made or lost. |
| <span class="member writes">places orders</span> | [`add_to_holdings`](holdings.md#add_to_holdings) | Buys more of this share to keep. |
| <span class="member writes">places orders</span> | [`reduce_holdings`](holdings.md#reduce_holdings) | Sells some of the shares held, without selling more than are free. |
| <span class="member writes">places orders</span> | [`liquidate_holdings`](holdings.md#liquidate_holdings) | Sells every share held that is free to sell. |

## The account

`Account` acts on the whole account rather than on one instrument. Its one member is the kill switch.

| Kind | Member | Description |
|---|---|---|
| <span class="member writes">places orders</span> | [`flatten`](account.md#flatten) | Cancels every open order at every broker, then closes every position in the account. |

## The UBI client

`UnifiedBrokerInterface` is the HTTP client every instrument shares. You rarely call it directly, but it is how you reach a UBI route the library does not wrap.

| Kind | Member | Description |
|---|---|---|
| <span class="member method">method</span> | [`connect`](client.md#connect) | Exchanges the api key and secret for a new access token. |
| <span class="member method">method</span> | [`disconnect`](client.md#disconnect) | Revokes the access token in force on the server. |
| <span class="member method">method</span> | [`status`](client.md#status) | Reports whether the session is connected and when its token expires. |
| <span class="member method">method</span> | [`get`](client.md#get) | Sends a GET request. |
| <span class="member method">method</span> | [`post`](client.md#post) | Sends a POST request. |
| <span class="member method">method</span> | [`put`](client.md#put) | Sends a PUT request. |
| <span class="member method">method</span> | [`patch`](client.md#patch) | Sends a PATCH request. |
| <span class="member method">method</span> | [`delete`](client.md#delete) | Sends a DELETE request. |

## Reference pages

Two pages support all the others. [Vocabulary](vocabulary.md) lists every plain string the library passes through, such as `"buy"`, `"limit"` and `"cnc"`, in the style of Kite's glossary of constants. [Errors](errors.md) lists every exception, which HTTP status from UBI raises it, and what to do next.
