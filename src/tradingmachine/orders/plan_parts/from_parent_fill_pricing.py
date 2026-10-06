"""The `from_parent_fill` pricing rule of a plan: the second leg of a spread priced from what the first leg filled at.

UBI works out the price that makes the two legs add up to `net_price`, the net debit per unit, which is positive when the spread costs money and negative for a credit. The first leg's side signs its average fill, a buy costing and a sell bringing money in, and the second leg's price is the net less that, signed by the second leg's own side. Each new order of the second leg is priced so that it and the second leg's earlier orders together average the price the net needs, and is rounded to the second leg's tick in the caller's favour, down for a buy and up for a sell. A price at or below zero cannot be sent, so the order waits. The order must be the child of a `ThenPart` whose first plan is a single order, or UBI refuses the plan with `from_parent_fill_needs_then`.

Typical usage example:

  pricing = from_parent_fill_pricing.FromParentFillPricing(net_price=45.0)
  document = pricing.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class FromParentFillPricing(plan_part.PlanPart):
    """A pricing rule for a spread's second leg, priced from the first leg's fill to reach a net price.

    Attributes:
        net_price: The float net debit per unit in rupees, negative for a credit.
    """

    def __init__(self, *, net_price: float):
        """Initialises the rule with the net price aimed at.

        Args:
            net_price: The float net debit per unit in rupees that the two legs should add up to, positive when the spread costs money and negative for a credit.

        Raises:
            Nothing.
        """
        self.net_price = net_price

    def document(self) -> dict:
        """Builds the `from_parent_fill` pricing object UBI reads.

        Returns:
            A dict with the single key `from_parent_fill`, whose value holds `net_price`.

        Raises:
            Nothing.

        Examples:
            Print the rule for a spread that should cost 45 rupees a unit:

            ```python
            from tradingmachine.orders.plan_parts import from_parent_fill_pricing

            pricing = from_parent_fill_pricing.FromParentFillPricing(net_price=45.0)
            print(pricing.document())
            ```

            Print a credit spread whose second leg, a buy, is priced from the first leg's sale to bring in 30 rupees a unit:

            ```python
            from tradingmachine.orders.plan_parts import from_parent_fill_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import then_part

            part = then_part.ThenPart(
                first=order_part.OrderPart(transaction_type="sell"),
                each_fill=order_part.OrderPart(
                    transaction_type="buy",
                    pricing=from_parent_fill_pricing.FromParentFillPricing(
                        net_price=-30.0,
                    ),
                ),
            )
            print(part.document())
            ```
        """
        return {
            "from_parent_fill": {
                "net_price": self.net_price,
            },
        }
