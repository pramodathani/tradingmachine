# data/instruments/indmoney.py

IND Money is the only one of the ten brokers whose instrument master is not public. It serves three CSV files, for equity, F&O and index, behind an `Authorization` header carrying an access token. An unauthenticated request returns HTTP 400.

## No API wrapper

The token is read from `indmoney_configuration["access_token"]`, which comes from `BLACK_BOX_INDMONEY_ACCESS_TOKEN` in `.env`, and passed straight to `requests`. This module deliberately builds no login flow and no broker client class: generating a token needs an API key, an MPIN and a TOTP secret, and that machinery is out of proportion to fetching a file once a day.

A token is generated separately from `https://api.indstocks.com/generate/token` and lasts twenty-four hours. Generating a new one revokes the previous one, so a token in use elsewhere should not be regenerated casually.

## Not yet verified against the live endpoint

No token was available when this module was written, so it has never run against the real endpoint. Two things are therefore provisional and must be confirmed on the first successful run.

The natural key, exchange plus segment plus security identifier, was carried over from how `unified_broker_interface` de-duplicates the same source rather than observed here.

There is no `100_instruments_indmoney.sql`. The columns cannot be known without downloading the file, so the DDL has to be written after the first successful download, from the cleaned column list, exactly as the other nine were.
