# src/tradingmachine/ubi_client/token_sources.py

A token source is the object `UnifiedBrokerInterface` asks for its access token. The module was split out of `client.py` on 2026-09-26, when instruments_explorer started using this library, because that project must not obtain tokens the way tradingmachine had until then.

## Why tokens needed a pluggable source

UBI holds one access token for the whole application. Until 2026-09-26 this library always connected on first use, with the key and secret from its own MongoDB. instruments_explorer's rule is the opposite: use the token UBI has stored and connect only when there is none, because a connect used to log every other UBI client out. UBI has softened that since (a connect now hands back the token already in force when it was issued after the most recent 07:00), but the first connect after 07:00 still replaces the token, and instruments_explorer keeps its rule.

Rather than add flags to the client, the choice of where tokens come from became an object. The client knows only four calls:

| Method | Called when |
|---|---|
| `current_token(client)` | Before every authenticated request |
| `token_after_refusal(client, refused_token)` | Once, after UBI answers 401 |
| `connect(client)` | When a caller calls `UnifiedBrokerInterface.connect` |
| `forget()` | After `UnifiedBrokerInterface.disconnect` |

The client holds its token lock around every one of these calls, so a source never needs its own lock. Each source receives the client as an argument rather than holding it, so one source object is not tied to a client at construction and there is no reference cycle.

## The sources

- `TokenSource` is the base, whose methods raise `NotImplementedError`. It is a plain class rather than an `abc.ABC`, following the shallow-base pattern used elsewhere in the library, such as `PriceAnalysis`.
- `CredentialTokenSource(api_key, api_secret)` remembers the token it last obtained and connects when it has none. After a refusal it connects again unless its remembered token has already changed, which is what makes concurrent refusals share one connect.
- `MongoCredentialTokenSource(project_configuration)` reads the key and secret from this project's MongoDB `settings` collection when it is created, then behaves as `CredentialTokenSource`. This is exactly the old `UnifiedBrokerInterface._load_credentials`, moved, including its error messages, so a client built without a token source still raises the same `ValueError` from its constructor when the settings document is missing.
- `tradingmachine.ubi_stores.stored_login_token_source.StoredLoginTokenSource` reads UBI's own stored token. It lives in `tradingmachine.ubi_stores` rather than here so that importing the REST client never imports `redis`.

`SETTINGS_BROKER_NAME` moved here with the MongoDB read. `client.SETTINGS_BROKER_NAME` still exists and refers to it, for any caller that imported it from the client.

The `client` import is only for type annotations and sits in an `if TYPE_CHECKING:` block, because `client.py` imports this module and a runtime import back would be circular.
