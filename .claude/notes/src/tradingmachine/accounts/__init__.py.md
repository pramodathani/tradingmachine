# src/tradingmachine/accounts/__init__.py

The package was added on 2026-09-26 for UBI's `POST /api/orders/flatten`, which acts on the whole account rather than on one instrument, so it has no natural home on `TradeableInstrument`. The user chose on 2026-09-26 to keep `liquidate_all_positions` scoped to one instrument and to put flatten on a separate account object, because flatten also cancels every open order on every instrument.

It is a package rather than a single module so that other account-wide reads, such as funds and the whole account's positions, have a place to go when they are wanted. Nothing is imported in `__init__.py`, for the same reason as the other packages.
