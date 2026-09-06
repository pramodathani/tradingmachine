# stream/shoonya/credentials.py

## Why this duplicates the other brokers' modules

The shape is a deliberate copy of `stream/flattrade/credentials.py`, which is itself a copy of the Dhan and Zerodha modules: one module per broker, four functions each, no shared helper. Shoonya and Flattrade are the two Noren brokers and the temptation to fold them into one module is strongest here of all, which is exactly why it is resisted. The two files already differ in the uid rule below, and a shared module would have to carry both rules behind a flag.

## The uid comes from settings, with no fallback chain

Flattrade's `stored_uid` prefers a `uid` written into last_login by the login and falls back to `settings["username"]`, because Flattrade's token exchange returns an account identifier that nothing else knows. Shoonya has no such value to prefer: `login_to_shoonya` drives the web login, exchanges the authorisation code at `GenAcsTok`, and stores only `susertoken` as the access token.

What it does do is send `settings["ucc_code"]` to `GenAcsTok` as `uid`, and type that same value into the login form as the user identifier. So the client code in the settings document is not a guess or a fallback — it is the value the account authenticates as, already proven correct every morning by the login job succeeding. Reading it directly is both simpler than Flattrade's chain and better grounded, and it keeps the whole Shoonya stream inside `stream/` with no change to `utilities/broker_login.py`.

If a live connect acknowledgement ever rejects it, the answer is that Shoonya's uid is not the client code after all, and the finding belongs in this note rather than in a second fallback.

## The staleness rule is the same conservative reading as the other brokers

A token issued yesterday may still technically work this morning, but `stored_access_token` returns None for anything not issued today. An expired Noren session is refused by the connect acknowledgement with `s: "Not_Ok"`, which is the same signature a capacity refusal would produce during probing. Refusing to hand out a stale token is what keeps those two apart.
