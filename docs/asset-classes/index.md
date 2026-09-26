# Asset classes

An instrument in this library is an object whose class says what kind of contract it is. There is a class for a share, one for a share future, one for an option on an index, and so on, 27 classes in all, spread over six family modules under `src/tradingmachine/assets/`. You pick the class, give it the few fields that identify one contract, and the constructor asks UBI which instrument that is. You never type a segment name such as `nse_equity_index_options` yourself, because the class already knows it.

The classes look alike, but what works on each one does not. UBI has live quotes for some segments and not others, stores candles for only a few, and cannot send an order for several kinds of instrument even though the class inherits the order methods. This page puts all of that in one place, and each family page explains the reasons.

## How the classes fit together

Every class inherits from one of two base classes. A class whose contracts can be traded inherits `TradeableInstrument`, which adds the order book, orders, positions and the price wrappers. An index inherits `NonTradeableInstrument`, which adds nothing and refuses anything that is not an index. Both inherit `Instrument`, which holds the identity fields, the candles and the quote, and which itself inherits the thirteen analysis classes described in [Analysis](../analysis/index.md).

The animated diagram below shows the six family modules feeding their classes up into the two base classes and then into `Instrument`.

<figure class="diagram">
--8<-- "docs/assets/diagrams/families.svg"
<figcaption>Orange dots follow the tradeable classes up through TradeableInstrument, and blue dots follow the four index classes up through NonTradeableInstrument. The orange dots entering Instrument from the right are the thirteen analysis classes it inherits.</figcaption>
</figure>

The funds module has only two classes and the mutual funds module only one, because UBI carries no futures or options on a fund, a trust or a mutual fund. The four families with derivatives each have six classes, following the same pattern: a cash instrument, its futures and its options, and an index, its futures and its options. [The instrument model](../architecture/instrument-model.md) explains the base classes in more depth.

## The whole matrix

The table below lists all 27 classes. "Named by" gives the constructor's arguments, every one of which is required. The last five columns say whether UBI serves a live quote, whether it stores candles, whether an order for the class can actually be placed, whether the class carries the holdings members, and which discovery class methods it offers.

:material-check: means yes, :material-close: means no, and :material-minus: means the segment holds no instruments at all in UBI, so the class resolves nothing today.

| Class | Module | UBI segment | Base | Named by | Quotes | Candles | Orders | Holdings | Discovery |
|---|---|---|---|---|:-:|:-:|:-:|:-:|---|
| [`Equity`][tradingmachine.assets.equities.Equity] | `equities` | `equities` | Tradeable | exchange, symbol | :material-check: | :material-check: | :material-check: | :material-check: | `search` |
| [`EquityFutures`][tradingmachine.assets.equities.EquityFutures] | `equities` | `equity_futures` | Tradeable | exchange, underlying, expiry | :material-check: | not checked | :material-check: | :material-close: | `expiries`, `contracts` |
| [`EquityOption`][tradingmachine.assets.equities.EquityOption] | `equities` | `equity_options` | Tradeable | exchange, underlying, expiry, strike, option type | :material-check: | not checked | :material-check: | :material-close: | `expiries`, `strikes`, `chain` |
| [`EquityIndex`][tradingmachine.assets.equities.EquityIndex] | `equities` | `equity_indices` | NonTradeable | exchange, symbol | :material-check: | :material-check: | :material-close: | :material-close: | `search` |
| [`EquityIndexFutures`][tradingmachine.assets.equities.EquityIndexFutures] | `equities` | `equity_index_futures` | Tradeable | exchange, underlying, expiry | :material-check: | not checked | :material-check: | :material-close: | `expiries`, `contracts` |
| [`EquityIndexOption`][tradingmachine.assets.equities.EquityIndexOption] | `equities` | `equity_index_options` | Tradeable | exchange, underlying, expiry, strike, option type | :material-check: | not checked | :material-check: | :material-close: | `expiries`, `strikes`, `chain` |
| [`FixedIncome`][tradingmachine.assets.fixed_income.FixedIncome] | `fixed_income` | `fixed_income` | Tradeable | exchange, symbol (an ISIN) | :material-close: | :material-close: | :material-close: | :material-check: | `search` |
| [`FixedIncomeFutures`][tradingmachine.assets.fixed_income.FixedIncomeFutures] | `fixed_income` | `fixed_income_futures` | Tradeable | exchange, underlying, expiry | :material-check: | :material-close: | :material-check: | :material-close: | `expiries`, `contracts` |
| [`FixedIncomeOption`][tradingmachine.assets.fixed_income.FixedIncomeOption] | `fixed_income` | `fixed_income_options` | Tradeable | exchange, underlying, expiry, strike, option type | :material-check: | :material-close: | :material-check: | :material-close: | `expiries`, `strikes`, `chain` |
| [`FixedIncomeIndex`][tradingmachine.assets.fixed_income.FixedIncomeIndex] | `fixed_income` | `fixed_income_indices` | NonTradeable | exchange, symbol | :material-close: | :material-close: | :material-close: | :material-close: | `search` |
| [`FixedIncomeIndexFutures`][tradingmachine.assets.fixed_income.FixedIncomeIndexFutures] | `fixed_income` | `fixed_income_index_futures` | Tradeable | exchange, underlying, expiry | :material-check: | :material-close: | :material-check: | :material-close: | `expiries`, `contracts` |
| [`FixedIncomeIndexOption`][tradingmachine.assets.fixed_income.FixedIncomeIndexOption] | `fixed_income` | `fixed_income_index_options` | Tradeable | exchange, underlying, expiry, strike, option type | :material-minus: | :material-minus: | :material-minus: | :material-close: | `expiries`, `strikes`, `chain` |
| [`Commodity`][tradingmachine.assets.commodities.Commodity] | `commodities` | `commodities` | Tradeable | exchange, symbol | :material-close: | :material-close: | :material-close: | :material-close: | `search` |
| [`CommodityFutures`][tradingmachine.assets.commodities.CommodityFutures] | `commodities` | `commodity_futures` | Tradeable | exchange, underlying, expiry | :material-check: | :material-check: | :material-check: | :material-close: | `expiries`, `contracts` |
| [`CommodityOption`][tradingmachine.assets.commodities.CommodityOption] | `commodities` | `commodity_options` | Tradeable | exchange, underlying, expiry, strike, option type | :material-check: | :material-check: | :material-check: | :material-close: | `expiries`, `strikes`, `chain` |
| [`CommodityIndex`][tradingmachine.assets.commodities.CommodityIndex] | `commodities` | `commodity_indices` | NonTradeable | exchange, symbol | :material-close: | :material-close: | :material-close: | :material-close: | `search` |
| [`CommodityIndexFutures`][tradingmachine.assets.commodities.CommodityIndexFutures] | `commodities` | `commodity_index_futures` | Tradeable | exchange, underlying, expiry | :material-check: | :material-check: | :material-check: | :material-close: | `expiries`, `contracts` |
| [`CommodityIndexOption`][tradingmachine.assets.commodities.CommodityIndexOption] | `commodities` | `commodity_index_options` | Tradeable | exchange, underlying, expiry, strike, option type | :material-check: | :material-check: | :material-check: | :material-close: | `expiries`, `strikes`, `chain` |
| [`Currency`][tradingmachine.assets.currencies.Currency] | `currencies` | `currencies` | Tradeable | exchange, symbol | :material-close: | :material-close: | :material-close: | :material-close: | `search` |
| [`CurrencyFutures`][tradingmachine.assets.currencies.CurrencyFutures] | `currencies` | `currency_futures` | Tradeable | exchange, underlying, expiry | nse only | :material-close: | :material-check: | :material-close: | `expiries`, `contracts` |
| [`CurrencyOption`][tradingmachine.assets.currencies.CurrencyOption] | `currencies` | `currency_options` | Tradeable | exchange, underlying, expiry, strike, option type | nse only | :material-close: | :material-check: | :material-close: | `expiries`, `strikes`, `chain` |
| [`CurrencyIndex`][tradingmachine.assets.currencies.CurrencyIndex] | `currencies` | `currency_indices` | NonTradeable | exchange, symbol | :material-minus: | :material-minus: | :material-minus: | :material-close: | `search` |
| [`CurrencyIndexFutures`][tradingmachine.assets.currencies.CurrencyIndexFutures] | `currencies` | `currency_index_futures` | Tradeable | exchange, underlying, expiry | :material-minus: | :material-minus: | :material-minus: | :material-close: | `expiries`, `contracts` |
| [`CurrencyIndexOption`][tradingmachine.assets.currencies.CurrencyIndexOption] | `currencies` | `currency_index_options` | Tradeable | exchange, underlying, expiry, strike, option type | :material-minus: | :material-minus: | :material-minus: | :material-close: | `expiries`, `strikes`, `chain` |
| [`ExchangeTradedFund`][tradingmachine.assets.funds.ExchangeTradedFund] | `funds` | `exchange_traded_funds` | Tradeable | exchange, symbol | :material-check: | :material-check: | :material-check: | :material-check: | `search` |
| [`InvestmentTrust`][tradingmachine.assets.funds.InvestmentTrust] | `funds` | `investment_trusts` | Tradeable | exchange, symbol | :material-check: | :material-close: | :material-check: | :material-check: | `search` |
| [`MutualFund`][tradingmachine.assets.mutual_funds.MutualFund] | `mutual_funds` | `mutual_funds` | Tradeable | exchange, symbol (a scheme code) | :material-close: | :material-close: | limit price only | :material-check: | `search` |

A few cells need a word of explanation, because the short form hides a condition.

- **Candles on equity derivatives are marked "not checked".** UBI's own documentation says no derivative bars are stored, but the commodity derivatives were measured on 2026-09-20 and do have candles, so that statement is out of date. Nobody has run `prices` on an equity future or option from this library, so the four cells are left unverified rather than guessed. `Equity` and `EquityIndex` do have candles: RELIANCE's are captured on the [Equities](equities.md) page, and NIFTY's were used for the beta check on 2026-09-14.
- **"Orders" means an order can actually be placed.** Every class built on `TradeableInstrument` has `place_order` and the thirty-two price wrappers, including `Commodity`, `Currency` and `FixedIncome`. For `Commodity` and `Currency`, UBI refuses the order. For `FixedIncome`, the only broker carrying cash bonds has no order symbol for them, so there is no broker to send the order to; this was read from the instrument data rather than tested. The cells therefore say no, and the family pages give the reasons.
- **The fixed income derivatives are marked as orderable, with a caution.** UBI appears to route them to the wrong venue. This was read from UBI's source and has never been tested with a real order, as the [Fixed income](fixed-income.md#a-routing-problem-in-ubi) page explains.
- **A mutual fund order is an ordinary `cnc` order.** It has no quote, so it needs a limit price, and whether a broker treats it as a subscription has not been tested.

## Coverage by family

The chart below counts, for each family, how many of its classes have each capability. The first bar in each group is the number of classes that resolve any instrument at all, so it shows how many of the family's classes are more than placeholders today. Candles on the four equity derivative classes are not counted, because they have not been checked.

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "For each asset family, the number of classes that resolve instruments, have quotes, have candles, can be ordered and carry holdings.",
  "width": "container",
  "height": 360,
  "data": {
    "values": [
      {"family": "Equities", "capability": "1. Resolves instruments", "classes": 6},
      {"family": "Equities", "capability": "2. Live quotes", "classes": 6},
      {"family": "Equities", "capability": "3. Candles", "classes": 2},
      {"family": "Equities", "capability": "4. Can be ordered", "classes": 5},
      {"family": "Equities", "capability": "5. Holdings", "classes": 1},
      {"family": "Fixed income", "capability": "1. Resolves instruments", "classes": 5},
      {"family": "Fixed income", "capability": "2. Live quotes", "classes": 3},
      {"family": "Fixed income", "capability": "3. Candles", "classes": 0},
      {"family": "Fixed income", "capability": "4. Can be ordered", "classes": 3},
      {"family": "Fixed income", "capability": "5. Holdings", "classes": 1},
      {"family": "Commodities", "capability": "1. Resolves instruments", "classes": 6},
      {"family": "Commodities", "capability": "2. Live quotes", "classes": 4},
      {"family": "Commodities", "capability": "3. Candles", "classes": 4},
      {"family": "Commodities", "capability": "4. Can be ordered", "classes": 4},
      {"family": "Commodities", "capability": "5. Holdings", "classes": 0},
      {"family": "Currencies", "capability": "1. Resolves instruments", "classes": 3},
      {"family": "Currencies", "capability": "2. Live quotes", "classes": 2},
      {"family": "Currencies", "capability": "3. Candles", "classes": 0},
      {"family": "Currencies", "capability": "4. Can be ordered", "classes": 2},
      {"family": "Currencies", "capability": "5. Holdings", "classes": 0},
      {"family": "Funds and trusts", "capability": "1. Resolves instruments", "classes": 2},
      {"family": "Funds and trusts", "capability": "2. Live quotes", "classes": 2},
      {"family": "Funds and trusts", "capability": "3. Candles", "classes": 1},
      {"family": "Funds and trusts", "capability": "4. Can be ordered", "classes": 2},
      {"family": "Funds and trusts", "capability": "5. Holdings", "classes": 2},
      {"family": "Mutual funds", "capability": "1. Resolves instruments", "classes": 1},
      {"family": "Mutual funds", "capability": "2. Live quotes", "classes": 0},
      {"family": "Mutual funds", "capability": "3. Candles", "classes": 0},
      {"family": "Mutual funds", "capability": "4. Can be ordered", "classes": 1},
      {"family": "Mutual funds", "capability": "5. Holdings", "classes": 1}
    ]
  },
  "mark": {"type": "bar", "tooltip": true},
  "encoding": {
    "y": {"field": "family", "type": "nominal", "title": null, "sort": ["Equities", "Fixed income", "Commodities", "Currencies", "Funds and trusts", "Mutual funds"]},
    "yOffset": {"field": "capability", "type": "nominal"},
    "x": {"field": "classes", "type": "quantitative", "title": "Number of classes", "axis": {"tickMinStep": 1}},
    "color": {"field": "capability", "type": "nominal", "title": "Capability", "legend": {"orient": "bottom", "columns": 3}}
  }
}
```

Three patterns stand out in the chart. Equities are the only family where nearly everything works. Commodities and currencies share a shape, in which only the derivatives are real contracts, but commodity derivatives have candles and currency derivatives do not. And holding is a separate idea from trading: a mutual fund can be held but has no quote, while a commodity future can be traded but never held.

## Holdings and positions are different things

A holding is something kept in the demat account overnight and beyond, such as shares bought for delivery. A position is what an order leaves open in a trading day or a derivatives contract, such as a long future. UBI reports holdings only for its cash segments, which are equities, exchange traded funds, investment trusts, mutual funds, fixed income and the catch-all `uncategorised`, so only the five classes on those segments carry the holdings members. Every class built on `TradeableInstrument` has the position members. [Holdings](../python-api/holdings.md) and [Positions](../python-api/positions.md) describe both sets.

## The families

Each family page lists its classes, explains how they are named, and records what UBI does and does not have for them.

<div class="grid cards" markdown>

-   :material-domain:{ .lg .middle } **Equities**

    ---

    Shares, indices, and the futures and options on each. The one family where quotes, candles, orders and holdings all work.

    [:octicons-arrow-right-24: Equities](equities.md)

-   :material-bank-outline:{ .lg .middle } **Fixed income**

    ---

    Bonds named by ISIN, rate indices, and interest rate futures and options. No candles, and no quote for a cash bond.

    [:octicons-arrow-right-24: Fixed income](fixed-income.md)

-   :material-gold:{ .lg .middle } **Commodities**

    ---

    MCX, NCDEX and NSE commodity derivatives, ordered in whole lots of quotation units. The derivatives have candles.

    [:octicons-arrow-right-24: Commodities](commodities.md)

-   :material-currency-inr:{ .lg .middle } **Currencies**

    ---

    Seven currency pairs and the bse's over-the-counter variants. Half the family is empty, and `lot_size` is a trap.

    [:octicons-arrow-right-24: Currencies](currencies.md)

-   :material-basket-outline:{ .lg .middle } **Funds and trusts**

    ---

    Exchange traded funds and investment trusts, which trade and are held exactly like shares.

    [:octicons-arrow-right-24: Funds and trusts](funds.md)

-   :material-piggy-bank-outline:{ .lg .middle } **Mutual funds**

    ---

    Schemes named by exchange code, held rather than traded, with no quote and no candles.

    [:octicons-arrow-right-24: Mutual funds](mutual-funds.md)

</div>

## What is not covered

UBI has one more segment, `uncategorised`, which collects instruments its mapping could not place anywhere else. It has no class here, because UBI does not accept orders for it. Every asset class the old tradingmachine project had is ported, so this is the only gap.
