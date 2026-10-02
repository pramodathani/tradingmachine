"""The `native_stop` pricing rule of a plan: a stop-limit order resting at the broker.

Because the stop rests at the broker, it still fires if UBI's order engine is down, unlike a stop made from a `PriceCrosses` or `Trails` trigger. With `exit_if_gapped`, a stop whose trigger the last price has already passed when it is sent goes as a limit two ticks past the other side's touch instead, because the broker would refuse such a stop or fill it wherever the gap left the price.

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
        exit_if_gapped: A bool that is True to send a stop the price has already passed as a marketable limit instead.
    """

    def __init__(
        self,
        *,
        trigger_price: float,
        limit_price: float,
        exit_if_gapped: bool = False,
    ):
        """Initialises the rule with the stop's trigger and limit.

        Args:
            trigger_price: The float trigger of the stop in rupees.
            limit_price: The float limit of the stop in rupees.
            exit_if_gapped: A bool that is True to send a stop whose trigger the last price has already passed as a limit two ticks past the other side's touch, rather than a stop the broker would refuse or fill wherever the gap left the price.

        Raises:
            Nothing.
        """
        self.trigger_price = trigger_price
        self.limit_price = limit_price
        self.exit_if_gapped = exit_if_gapped

    def document(self) -> dict:
        """Builds the `native_stop` pricing object UBI reads.

        Returns:
            A dict with the single key `native_stop`, whose value holds `trigger_price` and `limit_price`, and `exit_if_gapped` when it is True.

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

            Print a stop for a long position that goes as a marketable limit if the open has already gapped below 990:

            ```python
            from tradingmachine.orders.plan_parts import native_stop_pricing

            pricing = native_stop_pricing.NativeStopPricing(
                trigger_price=990.0,
                limit_price=988.0,
                exit_if_gapped=True,
            )
            print(pricing.document())
            ```
        """
        settings = {
            "trigger_price": self.trigger_price,
            "limit_price": self.limit_price,
        }
        if self.exit_if_gapped:
            settings["exit_if_gapped"] = True
        return {
            "native_stop": settings,
        }
