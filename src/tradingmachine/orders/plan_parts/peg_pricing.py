"""The `peg` pricing rule of a plan: a limit kept at a named place in the book and moved there as the book moves.

The reference is `own_touch`, the best price on the order's own side, so a buy sits on the bid; `mid`, halfway between the bid and the offer; or `opposite_touch`, the other side's best price, where the order fills at once. A positive `offset_ticks` moves the order away from filling and a negative one towards it. Every move passes UBI's repricing throttle, and a move that changes nothing is not sent.

Typical usage example:

  pricing = peg_pricing.PegPricing(reference="own_touch", offset_ticks=1)
  document = pricing.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class PegPricing(plan_part.PlanPart):
    """A pricing rule that keeps a limit at its reference in the book.

    Attributes:
        reference: The str place in the book, `own_touch`, `mid` or `opposite_touch`, or None for UBI's default of `own_touch`.
        offset_ticks: The int number of ticks away from the reference, positive away from filling and negative towards it, or None for UBI's default of 0.
        follows: A bool that is False to price the order at its reference once when it is sent and leave it there, or None for UBI's default of True.
        within_body_price: A bool that is True to treat the template's limit price as the worst price the order takes.
    """

    def __init__(
        self,
        *,
        reference: str | None = None,
        offset_ticks: int | None = None,
        follows: bool | None = None,
        within_body_price: bool = False,
    ):
        """Initialises the rule with its reference and settings.

        Args:
            reference: The str place in the book, `own_touch` for the order's own side, `mid` for halfway between the bid and the offer, or `opposite_touch` for the other side, or None for UBI's default of `own_touch`.
            offset_ticks: The int number of ticks away from the reference, positive away from filling and negative towards it, or None for UBI's default of 0.
            follows: A bool that is False to price the order at its reference once and leave it there, True to move it whenever the reference moves, or None for UBI's default of True.
            within_body_price: A bool that is True to treat the template's limit price as the worst price the order takes, resting at that price when the book shows no reference.

        Raises:
            Nothing.
        """
        self.reference = reference
        self.offset_ticks = offset_ticks
        self.follows = follows
        self.within_body_price = within_body_price

    def document(self) -> dict:
        """Builds the `peg` pricing object UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `peg`, whose value holds `reference`, `offset_ticks` and `follows` when they are set and `within_body_price` when it is True.

        Raises:
            Nothing.

        Examples:
            Print a peg that sits on the order's own side of the book with UBI's defaults:

            ```python
            from tradingmachine.orders.plan_parts import peg_pricing

            pricing = peg_pricing.PegPricing()
            print(pricing.document())
            ```

            Print a peg to the midpoint, one tick further from filling:

            ```python
            from tradingmachine.orders.plan_parts import peg_pricing

            pricing = peg_pricing.PegPricing(reference="mid", offset_ticks=1)
            print(pricing.document())
            ```

            Print a peg priced once at the own touch and kept within the template's limit price:

            ```python
            from tradingmachine.orders.plan_parts import peg_pricing

            pricing = peg_pricing.PegPricing(
                reference="own_touch",
                follows=False,
                within_body_price=True,
            )
            print(pricing.document())
            ```
        """
        settings = {}
        if self.reference is not None:
            settings["reference"] = self.reference
        if self.offset_ticks is not None:
            settings["offset_ticks"] = self.offset_ticks
        if self.follows is not None:
            settings["follows"] = self.follows
        if self.within_body_price:
            settings["within_body_price"] = True
        return {
            "peg": settings,
        }
