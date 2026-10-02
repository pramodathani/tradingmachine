"""The `limit_marketable` trigger of a plan: the other side of the book reaching the order's own limit price.

It holds a limit order in UBI's engine instead of at the exchange, and sends it only once it would fill straight away: for a buy, when the best offer is at or below the limit, and for a sell, when the best bid is at or above it. A quote marked stale never counts. The condition takes no settings and is written `{}`. The order is held at the body's own `LIMIT` price, so the template must be a limit order with a price and the order takes no pricing of its own; UBI refuses a pricing rule beside it. While the order is held, UBI's virtual book estimates how much a resting order at the same price would have filled, and keeps that as `missed_quantity` when the order is sent.

Typical usage example:

  condition = limit_marketable.LimitMarketable()
  document = condition.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class LimitMarketable(plan_part.PlanPart):
    """A condition that holds once the order's own limit price would fill at once."""

    def document(self) -> dict:
        """Builds the `limit_marketable` condition UBI reads.

        Returns:
            A dict with the single key `limit_marketable`, whose value is an empty dict, because the condition takes no settings.

        Raises:
            Nothing.

        Examples:
            Print the condition on its own:

            ```python
            from tradingmachine.orders.plan_parts import limit_marketable

            print(limit_marketable.LimitMarketable().document())
            ```

            Print an order held in the engine at the template's limit price, with no pricing of its own:

            ```python
            from tradingmachine.orders.plan_parts import limit_marketable
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                trigger=limit_marketable.LimitMarketable(),
            )
            print(part.document())
            ```

            Print a held limit order that is given up at twenty past three if it has not been sent by then:

            ```python
            from tradingmachine.orders.plan_parts import lifetime
            from tradingmachine.orders.plan_parts import limit_marketable
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                trigger=limit_marketable.LimitMarketable(),
                lifetime=lifetime.Lifetime(
                    at_time="15:20",
                    applies_to="waiting",
                ),
            )
            print(part.document())
            ```
        """
        return {
            "limit_marketable": {},
        }
