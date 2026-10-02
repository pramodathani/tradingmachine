"""The `cap` modifier of a plan's pricing: the most a buy will pay and the least a sell will take.

A cap is not a pricing rule of its own but a bound on one. Whatever the rule works out, when the order is sent and every time it is moved, a buy's limit is held at or below `worst_price` and a sell's at or above it. It goes beside the one pricing rule, as `OrderPart(pricing=..., cap=...)`, and an order has at most one cap. A market order has no limit to cap.

Typical usage example:

  cap = cap_modifier.CapModifier(worst_price=1010.0)
  document = cap.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class CapModifier(plan_part.PlanPart):
    """A bound on the price a pricing rule may set.

    Attributes:
        worst_price: The float worst price in rupees, the most a buy pays or the least a sell takes.
    """

    def __init__(self, *, worst_price: float):
        """Initialises the cap with its worst price.

        Args:
            worst_price: The float worst price in rupees, above zero, the most a buy pays or the least a sell takes.

        Raises:
            Nothing.
        """
        self.worst_price = worst_price

    def document(self) -> dict:
        """Builds the `cap` modifier object UBI reads in an order's pricing list.

        Returns:
            A dict with the single key `cap`, whose value holds `worst_price`.

        Raises:
            Nothing.

        Examples:
            Print a cap of 1010 rupees:

            ```python
            from tradingmachine.orders.plan_parts import cap_modifier

            cap = cap_modifier.CapModifier(worst_price=1010.0)
            print(cap.document())
            ```

            Print a buy that chases the offer but never pays more than 1010:

            ```python
            from tradingmachine.orders.plan_parts import cap_modifier
            from tradingmachine.orders.plan_parts import chase_pricing
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                pricing=chase_pricing.ChasePricing(step_ticks=1, step_seconds=5),
                cap=cap_modifier.CapModifier(worst_price=1010.0),
            )
            print(part.document())
            ```
        """
        return {
            "cap": {
                "worst_price": self.worst_price,
            },
        }
