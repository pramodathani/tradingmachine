# src/tradingmachine/ubi_stores/store_settings.py

Plain holders for the address and login of UBI's Redis and MongoDB, filled in by the caller. They exist so the store readers take one argument per store rather than six, and so that a program can pass UBI's settings without them passing through tradingmachine's `Configuration`, which reads tradingmachine's own `TRADINGMACHINE_*` variables and loads a `.env` into the process environment. `repr` leaves the password out.
