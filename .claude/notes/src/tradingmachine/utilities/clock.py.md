# src/tradingmachine/utilities/clock.py

`SystemClock.now()` returns `time.time()`. It exists so that `StoredLoginTokenSource` can be given a clock, and tests can give it `tests/fakes.py::FixedClock` to control token expiry and the connect cooldown without sleeping. It was added on 2026-09-26, copied from instruments_explorer's own `utilities/clock.py`.
