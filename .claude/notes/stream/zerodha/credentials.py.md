# stream/zerodha/credentials.py

Reads the API key and access token a Zerodha websocket connection needs, from the two MongoDB collections that already hold them.

## Two credentials with two different lifetimes

The websocket URL takes both, and they come from different places because they behave differently. The API key is a permanent property of the Kite Connect application and lives in the `settings` collection beside the login credentials. The access token is issued fresh every day by the login job cron runs at 07:00 and lands in `last_login`.

Nothing here obtains a token. That is `utilities/broker_login.py`'s job, and keeping the two apart matters: obtaining a token invalidates any previous one, so a streamer that logged in on its own would silently break whatever else is holding a session.

## A stale token is reported as no token

`stored_access_token` compares the stored `last_login` date against today and returns `None` if they differ, rather than returning yesterday's token.

This is worth the extra care because of how the failure would otherwise present. Zerodha rejects an expired token at the websocket handshake with a status code and no explanation, which is indistinguishable from the response to a wrong API key or to being over a connection limit. Since the supervisor uses handshake rejections to work out how many connections the account allows, an expired token would be misread as the account's limit being one connection lower than it is. Refusing to try a token that cannot work keeps that signal clean.

The date comparison is a string prefix, matching how `utilities/broker_login.py` writes and compares the field. It is not a datetime comparison because the stored value is a formatted string, and parsing it here only to compare the date part would be a more elaborate way of doing the same thing.

## Why this duplicates data/instruments/indmoney.py

`data/instruments/indmoney.py` contains a `stored_access_token` that does very nearly this. It was deliberately not extracted into a shared helper.

The two brokers agree today only by coincidence of both storing a token under a broker name. A shared version would have to grow a parameter the first time a broker stores something extra, as Kotak already does with its session id and base URL, and every later broker would add another. The result would be one function with a growing set of conditionals that no single broker's reader could follow, in place of two short functions each of which is complete on its own.

## The client is returned rather than hidden

`open_mongodb_database` returns the client alongside the database so the caller can close it. Every function here closes it in a `finally`. The shard reads credentials once at startup and then holds nothing, which is the point: a long-running process should not sit on a MongoDB connection it will not use again for fourteen hours.
