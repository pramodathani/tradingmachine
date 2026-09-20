# assets/exceptions.py

This module holds the three errors the instrument classes raise. It replaces `assets/exceptions.py` in the old tradingmachine project, which had a `TradingMachineException` root, numeric error codes, and about thirty classes for asset classes that are not ported yet.

Only the classes the ported code raises are kept. The port started with `InstrumentError`, `TradeableInstrumentError` and `NonTradeableInstrumentError`, and on 2026-09-20 gained the six the equity family raises: `EquityError`, `EquityFuturesError`, `EquityOptionError`, `EquityIndexError`, `EquityIndexFuturesError` and `EquityIndexOptionError`. The names end in `Error`, as the Google style guide requires, instead of the old `Exception` suffix. The numeric codes were dropped, because nothing read them. Classes for the other asset classes, and for holdings and orders, will be added when those are ported.

The six equity errors are flat siblings directly under `InstrumentError`, which the user chose on 2026-09-20. The old project rooted each asset class's five derivative errors in that class's own base, so `EquityFuturesException` inherited from `EquityException` and `except EquityException` caught the whole family. That reads oddly, because an index future is not a kind of equity, and the family catch it bought is rarely what you want: code that cares about one contract catches that contract's error, and code that cares about any instrument problem catches `InstrumentError`, which still works.

`TradeableInstrumentError` and `NonTradeableInstrumentError` inherit from `InstrumentError`, so `except InstrumentError` catches every instrument problem. In the old hierarchy they inherited from the root instead.

Transport failures stay as `ubi_client.exceptions` classes and are chained onto these with `raise ... from error` where one causes the other, as in the old design. That keeps "UBI could not answer" separate from "the instrument is wrong".
