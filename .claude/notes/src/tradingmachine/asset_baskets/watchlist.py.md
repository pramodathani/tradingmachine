# src/tradingmachine/asset_baskets/watchlist.py

`Watchlist` takes plain instruments rather than `BasketMember` objects, because a watchlist has no weights or quantities and asking for members would only add noise at the call site. It adds `add` and `rank_by`; everything else, including `top_gainers`, `breadth` and the equal-weighted candles, comes from `AssetBasket`.

Its constructor's argument is named `instruments`, the same as the module it imports. Inside `__init__` the name means the argument, and the annotations still resolve to the module because the class itself defines no `instruments` member; `asset_basket.py.md` explains why that matters.
