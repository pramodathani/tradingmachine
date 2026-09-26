# src/tradingmachine/orders/synthetic_order.py

`SyntheticOrder` is the shallow base the user's rules allow: it holds only what every synthetic type does identically. It stores the order template, builds the `synthetic` object from `SYNTHETIC_TYPE` and the subclass's `synthetic_fields()`, and sends the whole thing through `TradeableInstrument.place_order`. It validates nothing, because UBI validates the template exactly as it validates a plain order and each engine class checks its own fields, answering HTTP 400 with a message naming the field.

## Why `place()` goes through `place_order`

Every order in the library is built in one place. Sending through `place_order` means the body is assembled by the same code as a plain order, and every synthetic class is covered by the engine-mode check there, so a bracket cannot go out as an unprotected entry when UBI is in direct mode. The alternative, posting to `/api/orders/place` from here, would have been a second body builder and a second place to forget the check.

## The template

Every type sends an ordinary order body alongside its `synthetic` object, and UBI runs `PlaceOrderRequest` over it before the engine sees it, so even a type that never places the template as it stands needs a resolvable instrument, a side, a product, an order type and a quantity. Most types use the template for every order they send and change only what they must. The template's fields are public attributes on the object, so a caller can inspect or change an order before placing it.

`quantity` has no default and accepts None, like `place_order`'s, because a quantity reference can supply it. `price_reference` and `quantity_reference` are accepted by every class and passed through as plain dicts, because 28 of UBI's types resolve them.

## Keyword-only arguments

Every argument after the instrument is keyword-only. The classes take between fifteen and twenty-two arguments, and several are numbers in rupees that are easy to put in the wrong position, such as a stop's trigger and its limit, where a swap produces a stop that fires at the wrong level. Keyword-only arguments also let each subclass put its own required settings next to the template's required fields without Python's rule about defaults getting in the way.

## `synthetic`, `synthetic_fields` and `closes_position`

`synthetic_fields()` returns the type's settings as UBI names them, including those that are None, and the `synthetic` property drops the Nones so UBI applies its own defaults. The subclass therefore never repeats the "leave it out when it is None" loop. `closes_position` is sent only as a literal `True`, because UBI's engine counts only the literal `true` and ignores anything else, and a False would say nothing UBI does not already assume.

`SYNTHETIC_TYPE` on the base is `simple`, the type UBI runs when no `synthetic` object is sent, so the base alone would place a plain order. It is not meant to be used directly; `SimpleOrder` is the named class for that.

## What the answer looks like

A type that acts at once answers with the broker's answer and a `parent_id`; `freeze_slicer` and `ladder` add a list of `order_ids`. A type that waits for a price or a time answers HTTP 202, which the client treats as success, with an `outcome` of `armed` or `scheduled` and a `broker` and `order_id` of None. The `parent_id` is then the only handle on the order, and UBI has no REST route to list or cancel a parent, which is recorded in `docs/contributing/known-issues.md`.
