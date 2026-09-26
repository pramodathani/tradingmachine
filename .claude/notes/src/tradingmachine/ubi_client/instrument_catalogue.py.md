# src/tradingmachine/ubi_client/instrument_catalogue.py

`InstrumentCatalogue` was added on 2026-09-26 for instruments_explorer, a web application that shows every instrument UBI knows about and moved its UBI access onto this library that day.

## Why a separate class rather than more `Instrument` members

Building an `Instrument` sends `GET /api/instruments/details` from its constructor. That is right when a program works with a handful of named instruments, and wrong for an application that already holds the ids of 236,000 instruments from UBI's master and needs, say, the candles of 750 of them for a screener run: it would send 750 extra requests, and a chart for an unknown id would fail on the details lookup with a different error than the candles route gives. The catalogue therefore takes an instrument id per call and reads nothing until asked.

Every method returns UBI's answer unchanged, as a dict, so a caller that passes answers on to a browser sees exactly what UBI sent. The only wrapped answers are `prices_document`, which returns a `PricesDocument` whose `document` attribute is still the raw dict, and `open_master`, which returns an `InstrumentMasterStream`.

`Instrument.prices`, `Instrument.prices_document` and `Instrument.additional_details` build a catalogue over the instrument's client and call it, so the query parameters for the prices route are written in one place.

## Members

| Member | Route | Notes |
|---|---|---|
| `greeting` | `GET /api/` | No token needed, through `UnifiedBrokerInterface.greeting` |
| `segments` | `GET /api/instruments/segments` | The cheapest way to learn the mapping date |
| `mapping_date` | the same | UBI has no route of its own for it |
| `details(id)` | `GET /api/instruments/details` | |
| `additional_details(id)` | `GET /api/instruments/additional_details` | Not wrapped anywhere before this |
| `quote(id)` | `GET /api/instruments/quote` | |
| `prices_document(id, ...)` | `GET /api/instruments/prices` | The same parameters as `Instrument.prices` |
| `open_master(exchange, segment)` | `GET /api/instruments/master` | Streamed; see `instrument_master_stream.py.md` |

`segments` and `mapping_date` are properties because they take no argument, and they read UBI on every access, like `Instrument.quote`.

The family classes' discovery methods (`Equity.search`, `EquityOption.chain` and the rest) still read the master their own way, per segment and fully in memory. They were left alone because they return DataFrames per segment and their callers are small; moving them onto `InstrumentMasterStream` would be a separate change.
