# data/mapping/fyers.py

Ported from UBI's `back_office/instruments_v2/adapters/fyers.py`, classification side only. UBI's own module carried no order or quote implementation for this broker either, for the reason described at the end of this note.

## The two code-routed umbrellas

One `exchange_instrument_type` code can cover several segments, so both cash markets are routed in Python:

**BSE.** Exchange traded funds and investment trusts are drawn from *any* BSE row by cross-broker allowlist, checked before the type split — except on type 10, the index rows. Several BSE sector index short names ("ENERGY", "MOMENTUM") are exactly equal to a real, cross-broker-verified fund's own symbol, so without that exception the allowlist hijacks an index row into the fund segment before it ever reaches the index branch. Type 0 is equities. Type 50 splits on a suffix embedded in the ticker ("BSE:663HPCL31-F"): the clean equity suffixes are equities, a B suffix with a non-fund ISIN is an equity, and F or G with a real ISIN is a bond.

**NSE.** Types 0, 2, and 4 each leak a handful of investment trust rows carrying no marker of their own, so the allowlist is checked first, keyed on the same bare symbol the identity will later use. Types 0 and 3 are equities, 4 and 8 mutual funds, 9 exchange traded funds, 10 indices. The bond types 2, 5, 6, and 7 additionally require a real non-fund ISIN: the identity for that segment *is* the ISIN, so a row without one would collapse every such row onto a single identity. Index rows whose ticker begins `NSE:BHARATBOND-` or `NSE:NIFTYGS` are excluded, being bond-shaped rather than equity indices.

## The identity extraction trap

Where a segment names `symbol_ticker` as its identity source, the symbol is pulled out of `NSE:RELIANCE-EQ` with a pattern; every other segment reads its declared column plainly. An earlier version of UBI's adapter applied that pattern unconditionally to every segment's symbol. The pattern never matches a `BSE:` ticker, so it returned None for every BSE row, and since the instrument id is a pure hash of the identity tuple, each affected segment collapsed to exactly one instrument id. The failure is silent and total, which is why the extraction is conditional on what the segment actually declares.

## The ONMIBOR redirect

The canonical order lists `nse_fixed_income_futures` before `nse_fixed_income_index_futures`, so the broader rule claims the rate index futures first. UBI solved this by listing the narrower rule first; here the adapter redirects, the same pattern used for Dhan's fund segments and Groww's MCX index derivatives.

## Index aliases

Both index segments alias broker-specific names onto the canonical vocabulary: a fixed table for BSE, and for NSE a fixed table plus a live lookup against the day's already-written `instruments.master` index rows. That live lookup is why Fyers runs after Dhan and Groww in the processing order.

## Why there is no order side here

Fyers' `broker_symbol` is a description, not a tradeable ticker, and this project maps data only. When order routing is eventually built, the Fyers symbol must be constructed from the raw row — `symbol_ticker` and `fytoken` are both there — and verified live once. The chain from a mapped row back to the raw row is `broker_mappings.broker_token`, which holds `fytoken`, joined against `instruments.fyers` on that column and the download date; `resolution.resolve_raw_row` exists to make that lookup first-class.
