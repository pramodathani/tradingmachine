# assets/exceptions.py

This module holds the errors the instrument classes raise. It replaces `assets/exceptions.py` in the old tradingmachine project, which had a `TradingMachineException` root, numeric error codes, and about thirty classes for asset classes that are not ported yet.

Only the classes the ported code raises are kept. The port started with `InstrumentError`, `TradeableInstrumentError` and `NonTradeableInstrumentError`, and on 2026-09-20 gained the six the equity family raises: `EquityError`, `EquityFuturesError`, `EquityOptionError`, `EquityIndexError`, `EquityIndexFuturesError` and `EquityIndexOptionError`. The names end in `Error`, as the Google style guide requires, instead of the old `Exception` suffix. The numeric codes were dropped, because nothing read them. Later the same day it gained the six the fixed income family raises, named the same way: `FixedIncomeError`, `FixedIncomeFuturesError`, `FixedIncomeOptionError`, `FixedIncomeIndexError`, `FixedIncomeIndexFuturesError` and `FixedIncomeIndexOptionError`. The six the commodity family raises followed on the same day: `CommodityError`, `CommodityFuturesError`, `CommodityOptionError`, `CommodityIndexError`, `CommodityIndexFuturesError` and `CommodityIndexOptionError`. The six the currency family raises came last that day: `CurrencyError`, `CurrencyFuturesError`, `CurrencyOptionError`, `CurrencyIndexError`, `CurrencyIndexFuturesError` and `CurrencyIndexOptionError`. `ExchangeTradedFundError` and `InvestmentTrustError` followed with `assets/funds.py`. `MutualFundError` came last, with `assets/mutual_funds.py`, which completes the asset classes the old project had.

Every asset class's errors are flat siblings directly under `InstrumentError`, which the user chose for equities on 2026-09-20 and which fixed income follows. The old project rooted each asset class's five derivative errors in that class's own base, so `EquityFuturesException` inherited from `EquityException` and `except EquityException` caught the whole family. That reads oddly, because an index future is not a kind of equity, and the family catch it bought is rarely what you want: code that cares about one contract catches that contract's error, and code that cares about any instrument problem catches `InstrumentError`, which still works.

`TradeableInstrumentError` and `NonTradeableInstrumentError` inherit from `InstrumentError`, so `except InstrumentError` catches every instrument problem. In the old hierarchy they inherited from the root instead.

Transport failures stay as `ubi_client.exceptions` classes and are chained onto these with `raise ... from error` where one causes the other, as in the old design. That keeps "UBI could not answer" separate from "the instrument is wrong".

## OrderError

`OrderError` was added on 2026-09-20 with the buy and sell wrapper methods. It means an order cannot be priced, because the value it asks for is not there: a level the order book does not have, a mid price when one side of the book is empty, or a volume weighted average price the serving broker does not report. Nothing else raises it, and in particular `place_order`, `modify_order` and `cancel_order` do not, because they send what they are given and let UBI answer.

It inherits from `InstrumentError`, which the user chose on 2026-09-20. The old project deliberately did the opposite: its `OrderException` descended straight from the root, on the reasoning that an order problem is not an instrument problem, so `except InstrumentException` did not catch it. The choice here keeps one catch, `except InstrumentError`, working for every domain problem this package raises, which is the same reasoning that put the six equity errors under it.

A broker's refusal of an order is not an `OrderError`. That is `ubi_client.exceptions.OrderRejectedError`, from HTTP 422, and it stays on the transport side along with `ConflictError` and `OrderOutcomeUnknownError`.

## PositionError

`PositionError` was added on 2026-09-20 with the four members that change a position. It means the position cannot be changed as asked: nothing is held in the instrument, or nothing under the product named, or several are held and none was named, or the direction given contradicts the position, or the reduction is larger than the position itself.

It sits under `InstrumentError` beside `OrderError`, for the same reason and by the same choice: one `except InstrumentError` catches every domain problem this package raises.

The last of those cases deserves a word, because it looks like local validation of the kind this project avoids. Reducing a position by more than it holds is not something UBI would reject; it would accept the order and leave the account holding a new position the other way round. The method refuses it because that is not what it was asked to do, which is different from second-guessing a rule UBI already enforces.

## HoldingError

`HoldingError` was added on 2026-09-20 with the holdings methods on `Equity`, and `FixedIncome` raises it too. It means the holding cannot be changed as asked: the instrument is not held at all, or the quantity asked for is more than the units free to sell, or every unit held is pledged as collateral so none can be sold.

It sits under `InstrumentError` beside `OrderError` and `PositionError`, by the same choice and for the same reason.

It lives here rather than in an equity-specific place because anything that can be held raises it. `FixedIncome` already does, and exchange traded funds, investment trusts and mutual funds will when they are ported. The old project called it `HoldingException` and gave it the code 1505, rooted directly at its own `TradingMachineException` rather than under the instrument errors.
