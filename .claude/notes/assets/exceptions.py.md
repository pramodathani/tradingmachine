# assets/exceptions.py

This module holds the three errors the instrument classes raise. It replaces `assets/exceptions.py` in the old tradingmachine project, which had a `TradingMachineException` root, numeric error codes, and about thirty classes for asset classes that are not ported yet.

Only the classes the ported code raises are kept: `InstrumentError`, `TradeableInstrumentError` and `NonTradeableInstrumentError`. The names end in `Error`, as the Google style guide requires, instead of the old `Exception` suffix. The numeric codes were dropped, because nothing read them. Classes for futures, options, holdings and orders will be added when those classes are ported.

`TradeableInstrumentError` and `NonTradeableInstrumentError` inherit from `InstrumentError`, so `except InstrumentError` catches every instrument problem. In the old hierarchy they inherited from the root instead.

Transport failures stay as `ubi_client.exceptions` classes and are chained onto these with `raise ... from error` where one causes the other, as in the old design. That keeps "UBI could not answer" separate from "the instrument is wrong".
