# src/tradingmachine/asset_baskets/basket_member.py

`BasketMember` is one instrument with an optional `weight`, `quantity` and `average_price`. One small class serves every kind of basket rather than a subclass per kind, because the three fields are the only difference and each basket checks the ones it needs: `Portfolio` requires a quantity, a `stated` `Index` requires a weight, and `AssetBasket` requires that weights are given to every member or to none.

## The label

`label` gives each member a readable name such as `nse:INFY`, used as the index of every Series and DataFrame a basket returns. The exchange is part of it because the same symbol trades on the nse and the bse, and the holdings portfolio tested on 2026-09-28 held both `bse:ITC` and `nse:ONGC`. A future or option has no symbol, so its label is built from the underlying, the expiry, the strike and the option type.

## `document`

`document` stores both the instrument id and the readable identity fields. The id is what the store uses to rebuild the member, since UBI computes it deterministically and it is the same at every broker; the readable fields are there so a person reading MongoDB can tell what the basket holds, and so a member could be looked up by name if an id ever stopped resolving.
