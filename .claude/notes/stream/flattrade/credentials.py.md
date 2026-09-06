# stream/flattrade/credentials.py

## Why this duplicates the other brokers' modules

The shape is a deliberate copy of `stream/dhan/credentials.py` and `stream/zerodha/credentials.py`: one module per broker, four functions each, no shared helper. The copies are similar enough to invite one and different enough that one would grow arguments for every broker's quirks.

## Where the uid comes from, and why it is not simple

The connect message sends the same value as both `uid` and `actid`, but nothing in the original login flow stored one. `login_to_flattrade` signs in with `settings["username"]` and exchanges a request code for a token, and for a long time returned only `{"access_token": ...}`. Flattrade's token exchange response carries a `client` field — their own `token_generator/gettoken.py` reads it — which is the account identifier, so the login was extended to store it in last_login as `uid` alongside the token.

`stored_uid` therefore prefers the `uid` written by the login and falls back to `settings["username"]`, because the API login signs in with that username and an older last_login document predating the change carries no uid. Which of the two the connect acknowledgement actually accepts is a live-run question: if it rejects the fallback, the fix is to re-run the login, not to guess another field.

## The staleness rule is the same conservative reading as the other brokers

A token issued yesterday may still technically work this morning, but `stored_access_token` returns None for anything not issued today. An expired Flattrade session is refused by the connect acknowledgement with `s: "Not_Ok"`, and a refusal a stale token imitates would be indistinguishable from a capacity refusal during probing, which is exactly what the rule exists to prevent.