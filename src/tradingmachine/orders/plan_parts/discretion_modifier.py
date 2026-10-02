"""The `discretion` modifier of a plan's pricing: a visible limit that quietly takes a slightly worse price when one comes within reach.

The visible limit rests where the pricing rule put it. When the other side comes within `points` of it, UBI first reduces or cancels the resting order and then takes `quantity`, by default all that still rests, with a limit two ticks past the other side's touch but never past the visible price plus `points`. A buy resting at 1000 with 0.25 of discretion takes an offer of 1000.20. It goes beside the one pricing rule, as `OrderPart(pricing=..., discretion=...)`. It needs one visible limit, so UBI refuses it on a stop with `discretion_needs_limit` and with any execution other than all at once with `discretion_not_sliced`.

Typical usage example:

  discretion = discretion_modifier.DiscretionModifier(points=0.25)
  document = discretion.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class DiscretionModifier(plan_part.PlanPart):
    """A modifier that lets a resting limit take a price up to `points` worse than the one it shows.

    Attributes:
        points: The float distance in rupees past the visible price the order will go.
        quantity: The int quantity taken when the chance comes, or None for all that still rests.
    """

    def __init__(self, *, points: float, quantity: int | None = None):
        """Initialises the discretion with its distance and quantity.

        Args:
            points: The float distance in rupees past the visible price the order will go, above zero.
            quantity: The int quantity taken when the chance comes, at least 1, or None for all that still rests.

        Raises:
            Nothing.
        """
        self.points = points
        self.quantity = quantity

    def document(self) -> dict:
        """Builds the `discretion` modifier object UBI reads in an order's pricing list.

        Returns:
            A dict with the single key `discretion`, whose value holds `points`, and `quantity` when it is set.

        Raises:
            Nothing.

        Examples:
            Print a discretion of a quarter rupee that takes everything still resting:

            ```python
            from tradingmachine.orders.plan_parts import discretion_modifier

            discretion = discretion_modifier.DiscretionModifier(points=0.25)
            print(discretion.document())
            ```

            Print a buy resting on the bid that takes 50 at up to half a rupee more:

            ```python
            from tradingmachine.orders.plan_parts import discretion_modifier
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import peg_pricing

            part = order_part.OrderPart(
                pricing=peg_pricing.PegPricing(reference="own_touch"),
                discretion=discretion_modifier.DiscretionModifier(
                    points=0.5,
                    quantity=50,
                ),
            )
            print(part.document())
            ```
        """
        settings = {
            "points": self.points,
        }
        if self.quantity is not None:
            settings["quantity"] = self.quantity
        return {
            "discretion": settings,
        }
