"""The `native_stop` pricing rule of a plan: a stop-limit order resting at the broker.

Because the stop rests at the broker, it still fires if UBI's order engine is down, unlike a stop made from a `PriceCrosses` or `Trails` trigger.

Typical usage example:

  pricing = native_stop_pricing.NativeStopPricing(
      trigger_price=990.0,
      limit_price=988.0,
  )
  document = pricing.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class NativeStopPricing(plan_part.PlanPart):
    """A pricing rule that sends a stop-limit order to rest at the broker.

    Attributes:
        trigger_price: The float trigger of the stop in rupees.
        limit_price: The float limit of the stop in rupees.
    """

    def __init__(
        self,
        *,
        trigger_price: float,
        limit_price: float,
    ):
        """Initialises the rule with the stop's trigger and limit.

        Args:
            trigger_price: The float trigger of the stop in rupees.
            limit_price: The float limit of the stop in rupees.

        Raises:
            Nothing.
        """
        self.trigger_price = trigger_price
        self.limit_price = limit_price

    def document(self) -> dict:
        """Builds the `native_stop` pricing object UBI reads.

        Returns:
            A dict with the single key `native_stop`, whose value holds `trigger_price` and `limit_price`.

        Raises:
            Nothing.

        Examples:
            Print a sell stop triggered at 990 with its limit at 988:

            ```python
            from tradingmachine.orders.plan_parts import native_stop_pricing

            pricing = native_stop_pricing.NativeStopPricing(
                trigger_price=990.0,
                limit_price=988.0,
            )
            print(pricing.document())
            ```

            Print an order that protects a position with that stop:

            ```python
            from tradingmachine.orders.plan_parts import native_stop_pricing
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                side="protect",
                pricing=native_stop_pricing.NativeStopPricing(
                    trigger_price=990.0,
                    limit_price=988.0,
                ),
            )
            print(part.document())
            ```
        """
        return {
            "native_stop": {
                "trigger_price": self.trigger_price,
                "limit_price": self.limit_price,
            },
        }
