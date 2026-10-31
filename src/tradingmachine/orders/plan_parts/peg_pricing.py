"""The `peg` pricing rule of a plan: a limit kept at a named place in the book and moved there as the book moves.

The reference is `own_touch`, the best price on the order's own side, so a buy sits on the bid; `mid`, halfway between the bid and the offer; or `opposite_touch`, the other side's best price, where the order fills at once. A positive `offset_ticks` moves the order away from filling and a negative one towards it. Every move passes UBI's repricing throttle, and a move that changes nothing is not sent. When the book gives no price as the order is sent, because nobody is on the side the reference reads, no live quote has arrived or the quote is marked stale, `on_empty_book` decides what happens: `wait`, UBI's default, keeps the order waiting for a tick that does, and `refuse` ends it refused, which a plan with nothing else placed answers with HTTP 409 and sends nothing. `maximum_cost_bps` refuses the order in the same way, just before it is sent, when UBI's estimate of what filling the whole quantity against the visible book would cost is above that many basis points of the midpoint, or when the five visible levels do not hold the whole quantity. `reaches_size`, which needs the `opposite_touch` reference, keeps the limit no nearer than the deepest visible level on the other side that the unfilled quantity reaches, up to the fifth, so a large order takes those levels at once instead of chasing the price.

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
        on_empty_book: The str `wait` or `refuse`, what to do when the book gives no price as the order is sent, or None for UBI's default of `wait`.
        maximum_cost_bps: The float most, above zero, that crossing the spread may cost in basis points of the midpoint, or None for no maximum.
        reaches_size: A bool that is True to keep the limit as deep into the other side of the book as the unfilled quantity reaches, up to the fifth level.
    """

    def __init__(
        self,
        *,
        reference: str | None = None,
        offset_ticks: int | None = None,
        follows: bool | None = None,
        within_body_price: bool = False,
        on_empty_book: str | None = None,
        maximum_cost_bps: float | None = None,
        reaches_size: bool = False,
    ):
        """Initialises the rule with its reference and settings.

        Args:
            reference: The str place in the book, `own_touch` for the order's own side, `mid` for halfway between the bid and the offer, or `opposite_touch` for the other side, or None for UBI's default of `own_touch`.
            offset_ticks: The int number of ticks away from the reference, positive away from filling and negative towards it, or None for UBI's default of 0.
            follows: A bool that is False to price the order at its reference once and leave it there, True to move it whenever the reference moves, or None for UBI's default of True.
            within_body_price: A bool that is True to treat the template's limit price as the worst price the order takes, resting at that price when the book shows no reference. UBI refuses that price with HTTP 400 when it is not a whole number of ticks.
            on_empty_book: The str `wait` to keep the order waiting for a tick that carries its reference when the book gives no price as it is sent, or `refuse` to end it refused, which a plan with nothing else placed answers with HTTP 409, or None for UBI's default of `wait`.
            maximum_cost_bps: The float most, above zero, that crossing the spread may cost in basis points of the midpoint, as UBI estimates it from the visible book just before sending, or None for no maximum. Above it, or when the five visible levels do not hold the whole quantity, the order is refused as `refuse` refuses it.
            reaches_size: A bool that is True to keep the limit no nearer than the deepest visible level on the other side that the unfilled quantity reaches, up to the fifth. UBI refuses it with HTTP 400 unless `reference` is `opposite_touch`.

        Raises:
            Nothing.
        """
        self.reference = reference
        self.offset_ticks = offset_ticks
        self.follows = follows
        self.within_body_price = within_body_price
        self.on_empty_book = on_empty_book
        self.maximum_cost_bps = maximum_cost_bps
        self.reaches_size = reaches_size

    def document(self) -> dict:
        """Builds the `peg` pricing object UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `peg`, whose value holds `reference`, `offset_ticks`, `follows`, `on_empty_book` and `maximum_cost_bps` when they are set and `within_body_price` and `reaches_size` when each is True.

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

            Print a peg two ticks through the other side's best price that is refused, rather than left waiting, when nobody is on that side, which is the pricing of a `marketable_limit` order:

            ```python
            from tradingmachine.orders.plan_parts import peg_pricing

            pricing = peg_pricing.PegPricing(
                reference="opposite_touch",
                offset_ticks=-2,
                on_empty_book="refuse",
            )
            print(pricing.document())
            ```

            Print the pricing of a large marketable order that takes as many levels of the other side as its size needs, but is refused if crossing the spread would cost more than fifteen basis points:

            ```python
            from tradingmachine.orders.plan_parts import peg_pricing

            pricing = peg_pricing.PegPricing(
                reference="opposite_touch",
                offset_ticks=-2,
                on_empty_book="refuse",
                maximum_cost_bps=15,
                reaches_size=True,
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
        if self.on_empty_book is not None:
            settings["on_empty_book"] = self.on_empty_book
        if self.maximum_cost_bps is not None:
            settings["maximum_cost_bps"] = self.maximum_cost_bps
        if self.reaches_size:
            settings["reaches_size"] = True
        return {
            "peg": settings,
        }
