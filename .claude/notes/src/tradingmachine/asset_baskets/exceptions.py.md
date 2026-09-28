# src/tradingmachine/asset_baskets/exceptions.py

The package has its own exceptions module, like `unified_broker_interface/exceptions.py`, rather than adding to `assets/exceptions.py`, because a basket is not an instrument and `InstrumentError` would be the wrong root. All four errors derive from `AssetBasketError`, so a caller can catch the family. They are flat siblings, following the flat layout the user chose for the instrument errors.

`BasketMemberError` covers every problem with the members: an instrument UBI cannot find, one named twice, weights given to only some members, a Portfolio member without a quantity, and a member with no last price when a price is required. A failure of the whole request still arrives as the client's own error class, such as `BadRequestError`, because that is what actually happened.
