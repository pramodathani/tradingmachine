"""The `marketable` pricing rule of a plan: a limit a few ticks past the other side of the book.

UBI reads the opposite touch when it sends the order, the best offer for a buy and the best bid for a sell, and sets the limit `buffer_ticks` past it, so the order trades at once like a market order but cannot fill far from the book. With no book to price against, the order waits for the next tick.

Typical usage example:

  pricing = marketable_pricing.MarketablePricing(buffer_ticks=2)
  document = pricing.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class MarketablePricing(plan_part.PlanPart):
    """A pricing rule that sends a limit a few ticks past the opposite touch.

    Attributes:
        buffer_ticks: The int number of ticks past the opposite touch, or None for UBI's default of 2.
    """

    def __init__(
        self,
        *,
        buffer_ticks: int | None = None,
    ):
        """Initialises the rule with its buffer.

        Args:
            buffer_ticks: The int number of ticks past the opposite touch, or None for UBI's default of 2.

        Raises:
            Nothing.
        """
        self.buffer_ticks = buffer_ticks

    def document(self) -> dict:
        """Builds the `marketable` pricing object UBI reads.

        Returns:
            A dict with the single key `marketable`, whose value holds `buffer_ticks` when it is set.

        Raises:
            Nothing.

        Examples:
            Print the rule with UBI's default buffer:

            ```python
            from tradingmachine.orders.plan_parts import marketable_pricing

            print(marketable_pricing.MarketablePricing().document())
            ```

            Print the rule with a buffer of five ticks, for a thinly traded contract:

            ```python
            from tradingmachine.orders.plan_parts import marketable_pricing

            print(marketable_pricing.MarketablePricing(buffer_ticks=5).document())
            ```
        """
        settings = {}
        if self.buffer_ticks is not None:
            settings["buffer_ticks"] = self.buffer_ticks
        return {
            "marketable": settings,
        }
