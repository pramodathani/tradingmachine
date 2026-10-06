"""The `position` quantity of a plan: the size of the position held when the order fires, read at that moment.

An order with this quantity closes a position rather than trading a number named in advance, so its side must be `close`, and a `close` side needs this quantity. UBI first cancels every order resting on the instruments being closed, unless `cancel_resting_first` is False, so a stop or target left live cannot reopen the position, and then sends each broker's share to the broker that holds it, as a limit two ticks past the other side's touch. Such an order therefore takes no pricing or execution of its own. Nothing held ends the part with the reason `nothing_held` and the plan `completed` without an order.

Typical usage example:

  part = order_part.OrderPart(
      trigger=time_at.TimeAt("15:15"),
      side="close",
      quantity=position_quantity.PositionQuantity(product="intraday"),
  )
  document = part.document()
"""

from collections.abc import Sequence

from tradingmachine.assets import instruments
from tradingmachine.orders.plan_parts import plan_part


class PositionQuantity(plan_part.PlanPart):
    """A quantity that is the position held when the order fires, on one product and one or more instruments.

    Attributes:
        product: The str position product, `intraday`, `delivery` or `carry`, or None for the order's own product.
        held_instruments: The list of instruments.Instrument whose positions are closed, or None for the order's own instrument.
        every_instrument: A bool that is True to close the position in every instrument held on the product.
        ratio: The int ratio, 1 to close or 2 to close and open the same size the other way, or None for UBI's default of 1.
        cancel_resting_first: A bool that is False to leave resting orders alone before closing, or None for UBI's default of True.
    """

    def __init__(
        self,
        *,
        product: str | None = None,
        held_instruments: Sequence[instruments.Instrument] | None = None,
        every_instrument: bool = False,
        ratio: int | None = None,
        cancel_resting_first: bool | None = None,
    ):
        """Initialises the quantity with the positions it reads.

        Args:
            product: The str product as UBI names a position's product, `intraday`, `delivery` or `carry`, rather than an order's `mis`, `cnc` or `nrml`, or None for the order's own product.
            held_instruments: A sequence of instruments.Instrument objects whose positions are closed, or None for the order's own instrument; UBI refuses it beside `every_instrument`.
            every_instrument: A bool that is True to close every instrument held on the product.
            ratio: The int 1 to close the position, 2 to close it and open the reverse in one order, or None for UBI's default of 1.
            cancel_resting_first: A bool that is True to cancel every order resting on those instruments first, False to leave them, or None for UBI's default of True.

        Raises:
            Nothing.
        """
        self.product = product
        self.held_instruments = None
        if held_instruments is not None:
            self.held_instruments = list(held_instruments)
        self.every_instrument = every_instrument
        self.ratio = ratio
        self.cancel_resting_first = cancel_resting_first

    def document(self) -> dict:
        """Builds the `position` quantity UBI reads, holding every setting that is set.

        Returns:
            A dict with the single key `position`, whose value holds each of `product`, `ratio` and `cancel_resting_first` that is not None, the instruments as a list of their `instrument_ids`, and `every_instrument` when it is True.

        Raises:
            Nothing.

        Examples:
            Print a close of every intraday position at a quarter past three, which is what a square-off does:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import position_quantity
            from tradingmachine.orders.plan_parts import time_at

            part = order_part.OrderPart(
                trigger=time_at.TimeAt("15:15"),
                side="close",
                quantity=position_quantity.PositionQuantity(
                    product="intraday",
                    every_instrument=True,
                ),
            )
            print(part.document())
            ```

            Print a stop-and-reverse that closes the order's own position and opens the same size the other way once the price falls to 990:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import position_quantity
            from tradingmachine.orders.plan_parts import price_crosses

            part = order_part.OrderPart(
                trigger=price_crosses.PriceCrosses(level=990.0, direction="at_or_below"),
                side="close",
                quantity=position_quantity.PositionQuantity(ratio=2),
            )
            print(part.document())
            ```
        """
        settings = {}
        if self.product is not None:
            settings["product"] = self.product
        if self.held_instruments is not None:
            instrument_ids = []
            for instrument in self.held_instruments:
                instrument_ids.append(instrument.instrument_id)
            settings["instrument_ids"] = instrument_ids
        if self.every_instrument:
            settings["every_instrument"] = True
        if self.ratio is not None:
            settings["ratio"] = self.ratio
        if self.cancel_resting_first is not None:
            settings["cancel_resting_first"] = self.cancel_resting_first
        return {
            "position": settings,
        }
