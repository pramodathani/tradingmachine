# data/instruments/indmoney.py

IND Money is the only one of the ten brokers whose instrument master is not public. It serves three CSV files, for equity, F&O and index, behind an `Authorization` header carrying an access token. An unauthenticated request returns HTTP 400.

## The response is the CSV itself, not JSON

The endpoint answers with `content-type: text/csv` and the response body is the file — there is no JSON envelope holding a `"data"` field. This was written wrong at first, from an assumption carried over from `unified_broker_interface`, whose API wrapper hides the distinction: it tries the JSON body and falls back to passing the raw body through as the payload, so the same call looks like JSON-wrapping from the caller's side. The first live run failed with a JSON decode error and the raw probe settled it. `download()` therefore reads `response.text` straight into `read_csv`.

The request also sends `Content-Type: application/json`, matching what `unified_broker_interface`'s client sends. The endpoint answers the same way without it, but the header is kept so this request looks exactly like the one known to work.

## Verified against the live endpoint, 2026-09-04

The first successful download settled the two things that had been provisional. The natural key, exchange plus segment plus security identifier, dropped five exact duplicate rows from three files, consistent with the source carrying a handful of duplicates. The twenty-three column list is now written into `data/sql/ddl/100_instruments_indmoney.sql`, generated the same way as the other nine: from the cleaned output of a live download, not from documentation.

Two null patterns are worth knowing when reading the table. `isin` is null on the roughly eighty thousand F&O rows, because derivatives carry no ISIN. `delivery_unit` is null on every row because the source publishes it empty: each line ends with the comma after `GENERAL_FACTOR` and nothing following it. Both were checked against the raw file, so neither is a lost column.

## No API wrapper

The token reaches this module two ways, and the constructor takes an optional `access_token` argument so both work. `data/instruments/download_and_map.py` passes its `--indmoney-access-token` value through, and when that is omitted the constructor reads today's token from the MongoDB `last_login` collection, where `utilities/broker_login.py` records it. In both cases the token is passed straight to `requests`. This module deliberately builds no login flow of its own: generating a token needs an API key, an MPIN and a TOTP secret, and that machinery already exists in the login job.

## Why the token is not read from `.env` any more

It used to be, through `indmoney_configuration`, which meant the same secret lived in two places once the login job started writing it to MongoDB. Two sources for one credential is how they drift: the login job refreshes one of them daily and nothing refreshes the other, so the `.env` copy silently becomes a stale token that produces an authentication error with no explanation. The environment variable, its configuration entry and its `.env.example` line were all removed in the same change, so nothing points at the dead path.

## Why a stale token is rejected here rather than sent

`stored_access_token` returns nothing unless the stored token was issued today, using the same date comparison `broker_login.logged_in_today` uses. IND Money's tokens last twenty-four hours, and sending an expired one gets an authentication failure that says nothing about the cause. Failing early instead names the actual problem and the command that fixes it, which is the difference between a one-line log entry and a debugging session.

A token is generated separately from `https://api.indstocks.com/generate/token` and lasts twenty-four hours. Generating a new one revokes the previous one, so a token in use elsewhere should not be regenerated casually.
