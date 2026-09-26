# src/tradingmachine/ubi_stores/

This subpackage reads UBI's own Redis and MongoDB directly, and never writes to them. It was added on 2026-09-26, when instruments_explorer moved all of its UBI access onto this library, for two things UBI's REST API cannot give:

1. **The token UBI has already stored.** UBI has no route that returns its current token without connecting. `StoredLoginReader` reads it from the Redis hash `last_login` (field `unified_broker_interface`) or the MongoDB collection `last_login`, and `StoredLoginTokenSource` uses it, so a program can follow the rule of never connecting while a usable token exists.
2. **Many quotes at once.** UBI's quote routes take one instrument per request, and UBI has no bulk or streaming quote route. `LiveQuoteReader` reads the Redis hash `unified:quotes:live` with `HMGET`, which is what UBI's own order engine does (`utilities/order_engine/utilities/price_ticker.py`).

The code was ported from instruments_explorer's `access_token_provider.py`, `login_document.py`, `redis_reader.py` and `mongo_reader.py`, with their tests, and made synchronous: instruments_explorer calls it from worker threads. `redis.Redis` and `pymongo.MongoClient` are both safe to share between threads, because each keeps a connection pool.

## Why a separate subpackage

`import tradingmachine.ubi_client` should not import `redis`, and nothing that only talks to UBI's REST API should need UBI's store passwords. Keeping the direct store access here makes it visible: a program that imports `tradingmachine.ubi_stores` reads UBI's databases.

## Settings come from the caller

`RedisSettings` and `MongoSettings` are plain objects the calling program fills in, usually from UBI's own `.env`. Nothing here reads the environment or tradingmachine's `Configuration`, whose variables describe tradingmachine's own databases on ports 2002 and 2003, not UBI's on 1002 and 1003. Both classes leave the password out of their `repr`.

## Read-only, enforced by a test

`tests/test_ubi_stores.py::TestReadOnly` checks that `StoredLoginReader` and `LiveQuoteReader` have no public method beyond their reads and `close`, and scans the three modules' source for any Redis or MongoDB write command.

## Verified on 2026-09-26

Against the running UBI, with `may_connect=False`: the stored login was read from Redis and its expiry set on the client, RELIANCE's details, additional details, quote and 30 days of candles were read, `LiveQuoteReader` returned RELIANCE's and NIFTY's live quotes and skipped an unknown id, and the full instrument master streamed 525,519 instruments in 4.9 seconds. No connect was made, and UBI's stored token was the same before and after.
