# tests/fakes.py

Stand-ins that let the suite run without MongoDB, Redis or a real clock.

- `FakeMongoClientFactory` replaces `pymongo.MongoClient` through `monkeypatch.setattr(pymongo, "MongoClient", ...)`. Every module in the library calls `pymongo.MongoClient(...)` through the module rather than importing the class, so patching the attribute on `pymongo` reaches all of them. The factory records each client it creates, so a test can check that the client was closed and which timeout options it was given.
- `FakeCollection.find_one` matches documents field by field and honours only the `_id: 0` projection, which is all the library uses.
- `SettingsDatabase.with_credentials` builds the `settings` document that holds UBI's api key and secret, with the same values `tests/fake_ubi_server.py` accepts.
- `FixedClock` stands in for `tradingmachine.utilities.clock.SystemClock` where a test needs to control expiry and cooldown times.
