# stream/capacity.py

Remembers how much websocket streaming each broker actually allows, in MongoDB, so the number is measured once by hand and then reused rather than rediscovered every morning.

## Why the measurement is stored at all

Brokers publish limits that bear little relation to what they enforce. Zerodha documents 3 connections per API key and 3,000 instruments per connection, while the measured reality on 2026-09-05 was 25 connections and 108,431 instruments on one connection. The only way to learn the real numbers is to open connections until one is refused — which is exactly the behaviour that must not happen every morning, both because it wastes start-up time and because repeatedly leaning on an undocumented limit is the one thing that could make the broker start enforcing it.

So the capacity is a stored operational fact, and only `stream/zerodha/capacity_probe.py`, run deliberately and by hand, ever rewrites it. The supervisor and allocation code are readers, never writers.

## Why MongoDB and not Postgres

The same MongoDB database already holds this kind of state: the broker `settings` and the daily `last_login` results. Capacity belongs beside them, not in the market data database that holds observations. The practical second reason is that the `evidence` field has no fixed shape — it carries whatever the probe observed, which is currently verbatim probe logs — and a schemaless document takes that without ceremony.

The collection is named `stream_capacity` and holds one document per broker and feed, keyed on `broker_name` and `feed_name`, replaced whole on every write by `replace_one` with `upsert=True`. There is no history: the last measurement is the only one that matters operationally, and the evidence field preserves how it was obtained.

## Why the key gained a feed name

The original key was `broker_name` alone, and that held while Zerodha was the only broker. Dhan made it wrong: its live market feed and its full market depth sockets draw on one connection pool but are capped differently, so a single document per broker cannot hold both measurements without one overwriting the other. The key is now the pair, the document carries `feed_name`, and a legacy document lacking the field is simply replaced on the next write because the query no longer matches it. The `market_feed` default keeps Zerodha's probe and its stored document working unchanged.

Feed names in use are `market_feed` and `twenty_depth`; the two hundred level depth socket contributes no measurement of its own, because it takes one connection for one instrument by design.

## What the numbers mean

The two stored numbers are already safety-margined by the caller. `connection_count` is the measured simultaneous-connection limit minus a margin, not the raw measurement, and `instruments_per_connection` is a fraction of the largest subscription the broker honoured. Readers can use the numbers directly without knowing anything about how cautious to be — that judgement was made once, by the probe, when the evidence was fresh in front of it.

`last_refusal_reason` records how the broker said no, for example `handshake_status_429`. It is `None` when the probe stopped at its own ceiling rather than being refused, which is itself worth knowing: it means the stored count is a floor rather than a measured limit.

## The client is returned rather than hidden

`open_mongodb_database` returns the client alongside the database so the caller can close it. Every function here closes it in a `finally`. Readers call `read_capacity` once at start of day and then hold the numbers, not a MongoDB connection.