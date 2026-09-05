# utilities/broker_login.py

Logs in to all ten brokers once a day and stores each broker's access token in the MongoDB `last_login` collection. Every broker issues a token that expires at the end of the trading day, so this is meant to run each morning before the market opens.

Run it from the project root as `python -m utilities.broker_login`, not as `python utilities/broker_login.py`. The module imports `utilities.configuration`, which only resolves when the project root is the working directory.

## Where the credentials come from

Each broker needs a different set of inputs to log in: an API key and secret, a username and password, an MPIN, a TOTP secret, a UCC code, a vendor code. These live one document per broker in the MongoDB `settings` collection, keyed on `broker_name`, which is the same shape `unified_broker_interface` uses. The documents were mirrored across from that project's MongoDB rather than retyped.

The `settings` collection has a unique index on `broker_name`.

One wart came across with the mirror: Kotak's document spelled its password field `passwork`. It was renamed to `password` here on the user's instruction. Nothing reads it either way, because Kotak's login uses the API key, mobile number, UCC code, TOTP secret and MPIN instead. The typo still stands in `unified_broker_interface`'s own copy, so the two documents are no longer byte-for-byte identical.

## Where the tokens go

One document per broker in the `last_login` collection, `{broker_name, access_token, last_login}`, replaced in place on each successful login. This mirrors what `unified_broker_interface` writes, so a reader who knows one project can read the other.

Kotak is the exception that shapes the interface. Its API needs the session identifier and the account's own API host alongside the token, so its document also carries `sid` and `base_url`. That is why every login function returns a dictionary rather than a bare token string: the caller merges whatever the broker returned into the document instead of assuming a single field.

Unlike `unified_broker_interface`, nothing is written to Redis. That project caches `last_login` in Redis because its REST layer re-reads the token on every single API call; nothing in black_box does that yet.

## Tokens are not written to .env

An earlier draft of this script wrote `BLACK_BOX_<BROKER>_ACCESS_TOKEN` variables into `.env`. That was dropped in favour of MongoDB. A secret that rotates daily does not belong in a file that is read once at process start, and `.env` has no room for Kotak's extra session fields.

The `BLACK_BOX_INDMONEY_ACCESS_TOKEN` variable in `.env` is left alone, because `data/instruments/indmoney.py` still reads it through `indmoney_configuration`. That ingester could take its token from `last_login` instead, which would remove the last hand-managed token in the project.

## Why the flows are written out one per broker

Ten functions, one per broker, each self-contained and readable end to end. There is no shared request wrapper and no base class. The login flows genuinely differ — Zerodha, Shoonya and Stoxkart drive a web page in headless Chrome, the other seven talk to an API directly — and the parts that do look alike are two or three lines of error checking, which is cheaper to repeat than to hide behind an abstraction.

The flows were transcribed from `unified_broker_interface/stock_brokers/api/*.py`, where the same logic lives inside each broker class's `_connect` method. The transcription had to unpick each class's `_request` wrapper, because every broker unwraps its response body slightly differently before `_connect` sees it: Zerodha, Kotak and Stoxkart return the body's `data` field, Groww returns its `payload` field, Dhan and Shoonya return the whole body. Those differences are now visible at the point of use instead.

## The one time password guard is shared, and it is not optional

`generate_one_time_password` waits out the current thirty second window when fewer than four seconds of it remain, and every broker's login goes through it.

This started as an inline guard inside the Fyers flow alone, transcribed from `unified_broker_interface`, where a comment records that Fyers answers `-2` when a code is verified too close to the boundary. The first live run of this script showed the problem is not specific to Fyers: Dhan failed with `{"message":"Invalid TOTP","status":"error"}` while the other nine brokers logged in, and the identical credentials succeeded on an immediate retry. The code had simply expired between this process generating it and Dhan checking it.

That failure mode is invisible in testing and intermittent in production, which is exactly the kind a daily unattended job must not have. So the guard was lifted out of Fyers and put in front of all nine brokers that present a one time password. It is the one piece of genuinely shared mechanism in a module that otherwise keeps each broker's flow separate.

## Wisdom Capital's certificate, and what is actually bypassed

Wisdom Capital serves `trade.wisdomcapital.in` under a GoDaddy certificate issued to `*.ashlarindia.com`, which covers neither that hostname nor any Wisdom Capital domain. Python refuses the connection outright, and so does a browser until the warning is clicked through. The certificate is in date and the chain is genuine; only the name is wrong, which points at a server misconfiguration on their side rather than an interception.

Bypassing this was the user's explicit decision, taken after the failure and its cause were put to them.

What the bypass does *not* do is pass `verify=False`. That would be the one line answer, and it would accept literally any certificate, including a self signed one presented by whoever happens to sit between this host and the broker. The request carries the account's API key and secret, so that trade is a bad one.

Instead `HostnameCheckRelaxedAdapter` builds a default TLS context, sets `check_hostname` to False, and passes `assert_hostname=False` to the urllib3 pool. The chain must still lead to a trusted authority and the certificate must still be in date. Only the name match is dropped, which is precisely the one thing that is broken.

The adapter is mounted on a session scoped to the `https://trade.wisdomcapital.in` prefix, so it cannot leak into any other broker's requests.

This was checked against the `badssl.com` test endpoints rather than assumed:

| Certificate | Expected | Result |
| --- | --- | --- |
| `wrong.host` — name mismatch, chain trusted | allowed | connected, status 200 |
| `self-signed` | refused | `CERTIFICATE_VERIFY_FAILED` |
| `expired` | refused | `CERTIFICATE_VERIFY_FAILED` |
| `untrusted-root` | refused | `CERTIFICATE_VERIFY_FAILED` |

If Wisdom Capital ever fixes its certificate, deleting the adapter and the two lines that mount it restores ordinary verification with no other change.

## Running twice in one day

By default a broker whose stored `last_login` timestamp starts with today's date is skipped, and `--force` overrides that.

This is not tidiness. IND Money revokes the previous token when it issues a new one, so a second run in the same day would invalidate the token already in use. The date check is a cheap guard that needs nothing broker-specific.

The alternative, which `unified_broker_interface` uses, is to call each broker's profile endpoint and only log in when that call fails. That is more precise but needs ten more correctly shaped authenticated requests, one per broker, and each one is a fresh chance to get a header wrong.

## Failures are collected, not fatal

`log_in_to_brokers` catches everything per broker and carries on, so one broker being down or having rotated its password does not cost the other nine their tokens. The exit status is one if any broker failed, which is what a cron job needs to alarm on.

## Logging in changes state at the broker

This script re-authenticates against live broker accounts. For at least IND Money, and possibly others, a new token invalidates the previous one. `unified_broker_interface` logs in to the same ten accounts and stores tokens in its own database, so running this while that project holds live sessions will break them.
