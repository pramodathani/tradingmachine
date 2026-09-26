# src/tradingmachine/ubi_stores/live_quote_reader.py

`LiveQuoteReader.read` sends one `HMGET unified:quotes:live` per batch of `batch_size` (500) instrument ids and returns the quotes that exist. It replaces three uses in instruments_explorer: the live quote relay (twice a second, only for instruments a browser is watching), the option chain (a few hundred contracts every five seconds while the page is open) and the universe map (up to 236,000 instruments, cached for a minute).

Decisions:

- Repeated ids are read once, keeping their first order, so a caller never pays for duplicates.
- A missing field, text that is not JSON, or JSON that is not an object is left out rather than raised, because one damaged quote should not hide hundreds of good ones. The old instruments_explorer reader kept any valid JSON value; keeping only objects is stricter, and UBI only ever writes objects.
- A Redis failure becomes `tradingmachine.ubi_client.exceptions.UnreachableError`, so callers never need to import `redis` to catch it.
- 500 per round trip came from instruments_explorer, where it kept each `HMGET` under a few milliseconds.

The quote format is UBI's "unified quote", documented in UBI's `docs/architecture/contracts.md`. Times in it (`last_trade_time`, `exchange_time`, `received_at`, `unified_at`) are epoch seconds, and a quote from a broker that has gone silent stays in the hash with `stale: true`.
