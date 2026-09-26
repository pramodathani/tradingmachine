"""Indian market instruments as Python objects, traded through the Unified Broker Interface.

The library is six subpackages. `tradingmachine.assets` holds the instrument classes, one per asset class, and the candle analysis they inherit, which `CandleFrameAnalysis` also runs over candles a caller already has. `tradingmachine.orders` holds one class per synthetic order type UBI's order engine runs, and `tradingmachine.accounts` holds the account as a whole and its kill switch. `tradingmachine.ubi_client` is the REST client everything sends its requests through, with its token sources and the read-only `InstrumentCatalogue`. `tradingmachine.ubi_stores` reads UBI's stored token and live quotes straight from UBI's Redis and MongoDB, never writing. `tradingmachine.utilities` holds the configuration and the clock.

Nothing is imported here, because importing the library should not reach for the network, the databases or the `.env` file. Import the module you need instead.

Typical usage example:

  from tradingmachine.assets import equities

  infosys = equities.Equity(exchange="nse", symbol="INFY")
  print(infosys.last_price)
"""

import importlib.metadata

__version__ = importlib.metadata.version("tradingmachine")
