"""Baskets of instruments: portfolios, watchlists, indices and the contents of funds.

`tradingmachine.asset_baskets.asset_basket` holds `AssetBasket`, the shared base, which fetches live prices and candles for every member in one list request to UBI and inherits the same analysis and performance measures an instrument does. Each kind of basket is its own class in its own module: `Portfolio`, `Watchlist`, `Index`, `ExchangeTradedFundConstituents` and `MutualFundConstituents`. `BasketStore` keeps baskets in the project's MongoDB, and `BasketCsvImporter` fills it from a CSV file. Nothing is imported here, so import the module you need.

Typical usage example:

  from tradingmachine.asset_baskets import basket_store

  nifty_basket = basket_store.BasketStore().load("NIFTY")
  ratio = nifty_basket.sharpe_ratio(risk_free_rate=0.065, days=365)
"""
