# src/tradingmachine/ubi_stores/stored_login_token_source.py

`StoredLoginTokenSource` is a port of instruments_explorer's `AccessTokenProvider`, made synchronous and fitted to the `TokenSource` interface on 2026-09-26.

## The policy

1. Before each request, read UBI's stored login (Redis, then MongoDB) and use its token while it has more than `expiry_margin_seconds` (30) left.
2. After a 401, read the stored login again and use it if it holds a different usable token, which happens when another client connected in the meantime.
3. Only otherwise connect, and only when `may_connect` is true and no connect was attempted in the last `connect_cooldown_seconds` (60). The cooldown stops a loop of connects when UBI keeps refusing, for example when its clock and ours disagree about expiry.
4. When neither store can be read, raise `UnreachableError` rather than connect blindly: not knowing whether a token exists is not the same as knowing there is none.

The stored login is read on every request, as instruments_explorer did before. It costs one Redis `HGET`, a fraction of a millisecond locally, and it means a token another client obtained is picked up at once.

## Differences from the original

- It connects through `UnifiedBrokerInterface.exchange_credentials`, with UBI's own key and secret from UBI's MongoDB `settings`, so there is one connect implementation in the library.
- The lock moved to the client: `UnifiedBrokerInterface` holds its token lock around every call into a token source.
- It sets the client's `token_expires_at` to the stored expiry whenever it uses a stored token, so a status page can report when the token runs out.
- The connect message says that other clients were logged out only "if UBI issued a new one", because since UBI's change of 2026-09 a connect after 07:00 hands back the token already in force.
- `forget` does nothing: the token belongs to UBI's stores, and a disconnect is reflected there by UBI itself.
- `stored_login` is public for health checks, which instruments_explorer's status page uses to report the token's expiry.
