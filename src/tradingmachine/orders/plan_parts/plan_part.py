"""The shared base of every part of a plan order.

Every node, preset, trigger condition and pricing rule of a plan is a `PlanPart`, whose `document()` method gives the piece of UBI's `plan` object that the part stands for. The base holds no state of its own.

Typical usage example:

  part = price_crosses.PriceCrosses(level=995.0)
  if isinstance(part, plan_part.PlanPart):
      document = part.document()
"""


class PlanPart:
    """One piece of a plan order, which can describe itself as the object UBI's order engine reads."""

    def document(self) -> dict:
        """Builds the object UBI reads for this part.

        Returns:
            A dict holding exactly one key, the part's UBI name, whose value is the part's settings. The few parts that are entries of a list rather than named values, `Lifetime`, `PreOpenVenue`, `PaperVenue` and `StageRule`, hold their settings directly instead.

        Raises:
            NotImplementedError: The part is the base class itself, which stands for no part of a plan.

        Examples:
            See that every part of a plan is a `PlanPart`:

            ```python
            from tradingmachine.orders.plan_parts import plan_part
            from tradingmachine.orders.plan_parts import price_crosses

            part = price_crosses.PriceCrosses(level=995.0)
            print(isinstance(part, plan_part.PlanPart))
            print(part.document())
            ```

            See that the base class itself describes nothing:

            ```python
            from tradingmachine.orders.plan_parts import plan_part

            try:
                plan_part.PlanPart().document()
            except NotImplementedError as error:
                print(f"Refused: {error}")
            ```
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not describe a part of a plan"
        )
