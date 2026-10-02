"""The `follow_instrument` pricing rule of a plan: a limit moved by how far another instrument has moved since the order was sent.

The order starts at the template's own limit price, and from then on its price is that start price plus `delta` times the followed instrument's move, so a Nifty call bid with a delta of 0.5 rises by 20 when the index rises by 40, without reading the option's own thin book. The price stays between `lowest` and `highest`, never goes below one tick, and moves only when it would move by at least `step_ticks`. The template must be a limit order with a price, and the followed instrument must be another one than the order's own.

Typical usage example:

  index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
  pricing = follow_instrument_pricing.FollowInstrumentPricing(
      instrument=index,
      delta=0.5,
  )
  document = pricing.document()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders.plan_parts import plan_part


class FollowInstrumentPricing(plan_part.PlanPart):
    """A pricing rule that moves a resting limit after another instrument.

    Attributes:
        instrument: The instruments.Instrument followed, sent as its `instrument_id`.
        delta: The float number of rupees the price moves for each rupee the followed instrument moves.
        lowest: The float lowest price the order goes to, or None for no floor.
        highest: The float highest price the order goes to, or None for no ceiling.
        step_ticks: The int smallest move worth sending, in ticks, or None for UBI's default of 1.
    """

    def __init__(
        self,
        *,
        instrument: instruments.Instrument,
        delta: float,
        lowest: float | None = None,
        highest: float | None = None,
        step_ticks: int | None = None,
    ):
        """Initialises the rule with the instrument it follows and its settings.

        Args:
            instrument: The instruments.Instrument to follow, usually an option's underlying, which must not be the order's own instrument.
            delta: The float number of rupees the price moves for each rupee the followed instrument moves, which may be negative, as for a put.
            lowest: The float lowest price in rupees the order goes to, or None for no floor.
            highest: The float highest price in rupees the order goes to, or None for no ceiling.
            step_ticks: The int smallest move worth sending, in ticks, or None for UBI's default of 1.

        Raises:
            Nothing.
        """
        self.instrument = instrument
        self.delta = delta
        self.lowest = lowest
        self.highest = highest
        self.step_ticks = step_ticks

    def document(self) -> dict:
        """Builds the `follow_instrument` pricing object UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `follow_instrument`, whose value holds the followed instrument as its `instrument_id`, `delta`, and `lowest`, `highest` and `step_ticks` when each is set.

        Raises:
            Nothing.

        Examples:
            Print a rule that moves the price by half of the Nifty index's move:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders.plan_parts import follow_instrument_pricing

            index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pricing = follow_instrument_pricing.FollowInstrumentPricing(
                instrument=index,
                delta=0.5,
            )
            print(pricing.document())
            ```

            Print a rule for a put, which falls as the index rises, kept between 80 and 150 and moved in steps of two ticks:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders.plan_parts import follow_instrument_pricing

            index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pricing = follow_instrument_pricing.FollowInstrumentPricing(
                instrument=index,
                delta=-0.4,
                lowest=80.0,
                highest=150.0,
                step_ticks=2,
            )
            print(pricing.document())
            ```
        """
        settings = {
            "instrument_id": self.instrument.instrument_id,
            "delta": self.delta,
        }
        if self.lowest is not None:
            settings["lowest"] = self.lowest
        if self.highest is not None:
            settings["highest"] = self.highest
        if self.step_ticks is not None:
            settings["step_ticks"] = self.step_ticks
        return {
            "follow_instrument": settings,
        }
