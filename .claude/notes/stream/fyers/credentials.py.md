# stream/fyers/credentials.py

## Why this duplicates the other brokers' modules

The shape is a deliberate copy of `stream/flattrade/credentials.py`, which is itself a copy of the Dhan and Zerodha ones: one module per broker, no shared helper. The copies are similar enough to invite one and different enough that a shared helper would grow an argument for every broker's quirks. Fyers adds two quirks of its own, so the copy earns its place here more clearly than most.

## Three credentials rather than two, because there are two sockets

Every other broker in this project has one market data socket and so needs one pair of credentials. Fyers has two sockets that authenticate in completely different ways, and neither can use the other's form.

The quote socket at `wss://socket.fyers.in/hsm/v1-5/prod` sends no headers on the handshake at all. It authenticates with an in-band binary message whose token field is the `hsm_key` claim decoded out of the access token, not the access token itself. Sending the access token there does not work.

The tick-by-tick depth socket at `wss://rtsocket-api.fyers.in/versova` authenticates with an ordinary `Authorization` header whose value is the application identifier and the access token joined by a colon, which is what `authorization_header_value` builds.

So `websocket_credentials` returns all three and each connection driver takes the ones it needs.

## Fyers is the one broker whose token says when it expires

The other brokers' credential modules compare the login date to today's date and refuse anything not issued today. That rule is a conservative stand-in for an expiry nobody can see: a token issued yesterday evening may still work this morning, but treating it as usable risks mistaking a token expiry for a capacity refusal during probing, which is the failure this project most wants to avoid.

The Fyers access token is a JSON Web Token carrying an `exp` claim, so the expiry is not hidden and there is nothing to stand in for. `seconds_until_expiry` reads it directly and the error message says how long ago the token died, which is more useful than saying it was issued on the wrong date. The observed token expires the same evening it is issued, so in practice this rejects the same tokens the date rule would, but it does so for the real reason.

## The signature is deliberately not verified

`decode_token_claims` base64-decodes the payload and never checks the signature. Verifying would need a public key Fyers does not publish to us, in order to answer a question nobody is asking. Nothing in this project decides whether to trust the token; the broker decides that when the socket authenticates. All this module wants is what the broker itself wrote inside the token, and a forged token would fail at the socket regardless.

The padding in `base64.urlsafe_b64decode(payload + "===")` is deliberate over-padding. A JSON Web Token strips base64 padding, the segment length may need one, two or no padding characters, and Python ignores extra padding, so appending three always works and avoids computing the right number.

## Failure messages name the fix

Each error names the command that obtains a fresh token, because the person reading it at seven in the morning wants the next action rather than a diagnosis. This follows the Flattrade module, where the same message proved to be what was actually needed when a login had silently not run.
