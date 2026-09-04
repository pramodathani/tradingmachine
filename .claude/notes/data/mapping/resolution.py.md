# data/mapping/resolution.py

The three look-ups the mapped tables exist to serve. Ported in spirit from UBI's `back_office/instruments_v2/resolution.py`, simplified because this project's segment values are already the final stored form and need no translation on the way in or out.

## Why three functions and not two

The two obvious directions are identity to broker tokens, for placing an order or requesting a quote, and broker token to identity, for reading a position or holding back. The third, `resolve_raw_row`, exists because a broker's own endpoint sometimes needs an identifier the mapped tables have no column for.

Fyers is the known case and the reason this was designed in rather than added later. Its `broker_symbol` is `symbol_details`, a human-readable description such as "NIFTY 29 Sep 26 25000 CE", not a tradeable ticker. The real ticker is in the raw row's `symbol_ticker` column ("NSE:NIFTY26SEP25000CE"), verified on the 2026-09-04 snapshot by following exactly this chain. Because `broker_token` is each broker's own join key into its raw table, that row is always one lookup away, which is why no separate capture table was built.

## As-of semantics

Every function takes an `as_of_date` and uses the latest mapping on or before it, rather than the current state. A question asked about a past date therefore gets the answer that was true then. This matters most for derivatives, whose tokens are reused after expiry.

## The stable tie-break

`resolve_identity` uses `DISTINCT ON (broker_token) ... ORDER BY broker_token, mapping_date DESC, symbol ASC`. A token can point at more than one instrument when a broker's file reuses it — UBI found Flattrade's token 2202 double-assigned — so the most recent mapping wins and the symbol breaks any remaining tie. Without the second tie-break the answer would depend on row order and could change between identical calls.

## The broker name is not free text

`resolve_raw_row` interpolates the broker name into the table name, so it checks the name against the known broker list first and raises otherwise. `RAW_TOKEN_COLUMNS` records which raw column each broker's stored `broker_token` came from, which is the join key back into that broker's own file.
