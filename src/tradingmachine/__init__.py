"""Indian market instruments as Python objects, traded through the Unified Broker Interface.

The library is five subpackages. `tradingmachine.assets` holds the instrument classes, one per asset class, and the candle analysis they inherit. `tradingmachine.orders` holds one class per synthetic order type UBI's order engine runs, and `tradingmachine.accounts` holds the account as a whole and its kill switch. `tradingmachine.unified_broker_interface` is the REST client everything sends its requests through. `tradingmachine.utilities` holds the configuration they read.

Nothing is imported here, because importing the library should not reach for the network, the databases or the `.env` file. Import the module you need instead.

Typical usage example:

  from tradingmachine.assets import equities

  infosys = equities.Equity(exchange="nse", symbol="INFY")
  print(infosys.last_price)
"""

import importlib.metadata

__version__ = importlib.metadata.version("tradingmachine")
