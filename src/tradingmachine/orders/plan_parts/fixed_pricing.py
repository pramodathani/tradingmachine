"""The `fixed` pricing rule of a plan: a limit at a given price, or a market order.

It is the rule an order in a plan uses when it names none, taking the template's own order type and price. UBI writes its order type in capitals here, `LIMIT` or `MARKET`, unlike the template's lower-case `limit` and `market`.

Typical usage example:

  pricing = fixed_pricing.FixedPricing(price=1010.0, order_type="LIMIT")
  document = pricing.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class FixedPricing(plan_part.PlanPart):
    """A pricing rule that sends the order at a set price, or at market.

    Attributes:
        price: The float limit price in rupees, or None to use the template's price.
        order_type: The str order type, `LIMIT` or `MARKET`, or None to use the template's.
    """

    def __init__(
        self,
        *,
        price: float | None = None,
        order_type: str | None = None,
    ):
        """Initialises the rule with its price and order type.

        Args:
            price: The float limit price in rupees, or None to use the template's price.
            order_type: The str order type in capitals, `LIMIT` or `MARKET`, or None to use the template's.

        Raises:
            Nothing.
        """
        self.price = price
        self.order_type = order_type

    def document(self) -> dict:
        """Builds the `fixed` pricing object UBI reads.

        Returns:
            A dict with the single key `fixed`, whose value holds `price` and `order_type` when each is set.

        Raises:
            Nothing.

        Examples:
            Print a limit at 1010:

            ```python
            from tradingmachine.orders.plan_parts import fixed_pricing

            pricing = fixed_pricing.FixedPricing(price=1010.0, order_type="LIMIT")
            print(pricing.document())
            ```

            Print a market order, and the rule that keeps the template's own pricing:

            ```python
            from tradingmachine.orders.plan_parts import fixed_pricing

            print(fixed_pricing.FixedPricing(order_type="MARKET").document())
            print(fixed_pricing.FixedPricing().document())
            ```
        """
        settings = {}
        if self.price is not None:
            settings["price"] = self.price
        if self.order_type is not None:
            settings["order_type"] = self.order_type
        return {
            "fixed": settings,
        }
