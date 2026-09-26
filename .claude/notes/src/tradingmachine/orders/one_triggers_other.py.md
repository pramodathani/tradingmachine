# src/tradingmachine/orders/one_triggers_other.py

`OneTriggersOtherOrder` mirrors UBI's `oto` synthetic order type, `unified_broker_interface/utilities/order_engine/oto.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D1 one-triggers-other.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI reads `then` as an order body without a quantity and lays it over the whole template (`body.update(described)` in `oto.py`), then sets the quantity to what the first order filled and drops the tag. So the class does not take a `then` dict; it takes the six fields a second order sensibly changes as `then_transaction_type`, `then_order_type`, `then_price`, `then_trigger_price`, `then_product` and `then_validity`, and builds the dict itself. The side and the order type are required, which is a choice made here rather than UBI's rule: a `then` that changed neither would repeat the first order, which is never what an OTO is for.

Because the template is laid underneath, a template `price` is carried into a `then_order_type` of `market` and UBI refuses the market order that carries a price. UBI validates the child order before it sends the first one, so a dry run shows the refusal without placing anything. The docstring says so.
