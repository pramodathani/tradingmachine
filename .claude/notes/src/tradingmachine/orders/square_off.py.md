# src/tradingmachine/orders/square_off.py

`SquareOffOrder` mirrors UBI's `square_off` synthetic order type, `unified_broker_interface/utilities/order_engine/square_off.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row C4 own end-of-day square-off.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI's `SquareOff` decides the side, the order type and the quantity of every closing order from the positions, but the route still runs `PlaceOrderRequest` over the body first, so the body needs a valid side, order type and quantity. The class fills them with placeholders, `sell`, `market` and 1, and does not accept them from the caller, since a caller's values would be ignored. The instrument only anchors the request, which UBI's docstring on the class says plainly: it does not limit what is closed. `only_instruments` does, and is named that way rather than `instruments`, which would shadow the module of the same name inside the constructor.

The product appears twice, in two spellings, and this is the one trap in the type. UBI's comment on `SquareOff.product_to_close` says the closing orders are sent with the product from the body, on the order vocabulary (`MIS`, `CNC`, `NRML`), while `synthetic.product` filters the positions on the positions' vocabulary. Conflating the two produced "product must be one of CNC, MIS, NRML" in UBI's own history. The class takes one `product` on the order vocabulary, defaulting to `mis` because a square-off is an intraday habit, and translates it for the synthetic field with `POSITION_PRODUCT_FOR_ORDER_PRODUCT`. That comment calls the carry product `carryforward` while the positions document and this library's mapping say `carry`; the mapping's spelling is used, and a dry run would show a mismatch.

`closes_position` defaults to True here and only here, because every order a square-off sends is an exit, and a square-off that could not use the exit share of a broker's daily cap would fail on exactly the day that cap was used up. UBI never resolves price or quantity references for this type, so the class does not accept them.
