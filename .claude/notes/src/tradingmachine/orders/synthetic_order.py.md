# src/tradingmachine/orders/synthetic_order.py

`SyntheticOrder` is the shallow base the user's rules allow: it holds only what every synthetic type does identically. It stores the order template, builds the `synthetic` object from `SYNTHETIC_TYPE` and the subclass's `synthetic_fields()`, and sends the whole thing through `TradeableInstrument.place_order`. It validates nothing, because UBI validates the template exactly as it validates a plain order and each engine class checks its own fields, answering HTTP 400 with a message naming the field.

## Why `place()` goes through `place_order`

Every order in the library is built in one place. Sending through `place_order` means the body is assembled by the same code as a plain order, so a synthetic order and a plain one cannot drift apart. The alternative, posting to `/api/orders/place` from here, would have been a second body builder. Until 2026-09-27 `place_order` also refused to send a synthetic order when UBI placed orders directly, without its engine; UBI removed that mode that day, so the check went too.

## The template

Every type sends an ordinary order body alongside its `synthetic` object, and UBI runs `PlaceOrderRequest` over it before the engine sees it, so even a type that never places the template as it stands needs a resolvable instrument, a side, a product, an order type and a quantity. Most types use the template for every order they send and change only what they must. The template's fields are public attributes on the object, so a caller can inspect or change an order before placing it.

`quantity` has no default and accepts None, like `place_order`'s, because a quantity reference can supply it. `price_reference` and `quantity_reference` are accepted by every class and passed through as plain dicts, because 28 of UBI's types resolve them.

## Keyword-only arguments

Every argument after the instrument is keyword-only. The classes take between fifteen and twenty-two arguments, and several are numbers in rupees that are easy to put in the wrong position, such as a stop's trigger and its limit, where a swap produces a stop that fires at the wrong level. Keyword-only arguments also let each subclass put its own required settings next to the template's required fields without Python's rule about defaults getting in the way.

## `synthetic`, `synthetic_fields` and `closes_position`

`synthetic_fields()` returns the type's settings as UBI names them, including those that are None, and the `synthetic` property drops the Nones so UBI applies its own defaults. The subclass therefore never repeats the "leave it out when it is None" loop. `closes_position` is sent only as a literal `True`, because UBI's engine counts only the literal `true` and ignores anything else, and a False would say nothing UBI does not already assume.

`SYNTHETIC_TYPE` on the base is `simple`, the type UBI runs when no `synthetic` object is sent, so the base alone would place a plain order. It is not meant to be used directly; `SimpleOrder` is the named class for that.

## What the answer looks like

A type that acts at once answers with the broker's answer and a `parent_id`; `freeze_slicer` and `ladder` add a list of `order_ids`. Since 2026-09-27 the types that send several orders at once share one rule for the combined `outcome`: `accepted` when all were accepted, `partial` with HTTP 207 when some were, and `unknown` or `rejected` otherwise. HTTP 207 is a success status, so a partial answer is returned, and the caller must read each order's own outcome in it. A type that waits for a price or a time answers HTTP 202, which the client also treats as success, with an `outcome` of `armed` or `scheduled` and a `broker` and `order_id` of None.

## `parent_id`, `cancel()`, `parent`, `orders` and `trades`

The `parent_id` is the only handle on an order that has not reached a broker. When the package was written UBI had no route to read or cancel a parent, so the id was only returned. On 2026-09-27 UBI added `GET /api/orders/parents`, `DELETE /api/orders/parents` and a `parent_id` filter on the order and trade books, so `place()` now keeps the id on the object and the object can act on itself: `cancel()` cancels the parent and its resting legs, `parent` reads the engine's own record, and `orders` and `trades` read the broker orders and fills it has produced. They go through `TradeableInstrument` methods of the same names, so the routes are called from one place, and each refuses with `ValueError` before `place()` has run, or after a dry run, which records nothing and so gives no id.

`reduce_only` is sent only as a literal `True`, for the same reason as `closes_position`: UBI refuses anything but true or false, and a False says nothing UBI does not assume.

## `hold_limits` (2026-10-05)

UBI began holding limit orders in its virtual order book by default on 2026-10-03, the day it retired its fixed order classes and started running every type but `simple` and `plan` as a plan of the type's preset. Whether an order is held is decided by `hold_limits` in the `synthetic` object, and its default differs by type: eighteen types hold while UBI's `UNIFIED_BROKER_INTERFACE_API_ORDER_HOLD_LIMITS` switch is on, a hand-written plan follows the switch, and every other type does not hold.

Unlike `closes_position` and `reduce_only`, a False here is not what UBI assumes, because a ladder or a bracket now holds unless told otherwise. So the argument is a three-way `bool | None`: None leaves the field out and lets UBI apply the type's default, and True and False are both sent. It was added to the base class and to every one of the fifty-four subclasses, the way `reduce_only` was, rather than only to the eighteen holding types, because UBI reads the field on any type and the library validates nothing locally; a type that cannot be held refuses True with HTTP 400 and the rule `not_holdable`, and `simple` refuses True outright.

The same field exists on one order of a plan, which `OrderPart.hold_limits` sends. It matters most for follow-on orders such as a bracket's target, which the request's `hold_limits` never reaches.
