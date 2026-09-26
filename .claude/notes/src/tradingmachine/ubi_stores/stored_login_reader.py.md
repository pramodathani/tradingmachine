# src/tradingmachine/ubi_stores/stored_login_reader.py

`StoredLoginReader` combines instruments_explorer's `RedisReader.hash_get_json` and `MongoReader`, ported on 2026-09-26 and reduced to the three reads the token source needs.

- `stored_login` reads Redis first, because that is the copy UBI itself checks on every request (`blueprints/base.py`), and falls back to MongoDB, the record Redis is filled from. A Redis failure or unreadable JSON is logged as a warning and treated as "no document", so MongoDB is tried; a MongoDB failure after that raises `UnreachableError`.
- `api_credentials` reads UBI's own `settings` document. These are the same key and secret tradingmachine keeps a copy of in its own MongoDB, read here from UBI so that a program using this reader needs no copy.
- The MongoDB client gets the same number of milliseconds for server selection, connecting and each socket operation, as instruments_explorer's did, so an unreachable MongoDB fails within the timeout rather than pymongo's default of 30 seconds of server selection on top.

Both clients connect lazily, on the first read, so building a reader never fails because a store is down.
