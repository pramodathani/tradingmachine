"""The `option_model` pricing rule of a plan: an option's premium worked out from an implied volatility and kept current as the underlying moves.

UBI prices the order's option with the Black-76 model at the stated `volatility`, reading the option's strike, expiry and kind from its catalogue when the plan is placed, and re-prices it as the underlying moves and expiry nears. When the underlying is a future it is the forward; otherwise, as for the index, the spot is grown by `interest_rate` to expiry. The template's own price is the worst the order accepts, and the bounds and the step work as they do for `FollowInstrumentPricing`. An order whose instrument is not an option is refused.

Typical usage example:

  index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
  pricing = option_model_pricing.OptionModelPricing(
      instrument=index,
      volatility=14.0,
  )
  document = pricing.document()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders.plan_parts import plan_part


class OptionModelPricing(plan_part.PlanPart):
    """A pricing rule that prices an option from an implied volatility and its underlying.

    Attributes:
        instrument: The instruments.Instrument that is the option's underlying, sent as its `instrument_id`.
        volatility: The float implied volatility as a percentage, above zero and at most 500.
        interest_rate: The float yearly interest rate as a percentage, or None for UBI's default of 0.
        lowest: The float lowest price the order goes to, or None for no floor.
        highest: The float highest price the order goes to, or None for no ceiling.
        step_ticks: The int smallest move worth sending, in ticks, or None for UBI's default of 1.
    """

    def __init__(
        self,
        *,
        instrument: instruments.Instrument,
        volatility: float,
        interest_rate: float | None = None,
        lowest: float | None = None,
        highest: float | None = None,
        step_ticks: int | None = None,
    ):
        """Initialises the rule with the underlying, the volatility and its settings.

        Args:
            instrument: The instruments.Instrument that is the option's underlying, such as the index or a future on it.
            volatility: The float implied volatility as a percentage, such as 14.0 for 14%, above zero and at most 500.
            interest_rate: The float yearly interest rate as a percentage, used to grow a spot underlying to expiry, or None for UBI's default of 0.
            lowest: The float lowest price in rupees the order goes to, or None for no floor.
            highest: The float highest price in rupees the order goes to, or None for no ceiling.
            step_ticks: The int smallest move worth sending, in ticks, or None for UBI's default of 1.

        Raises:
            Nothing.
        """
        self.instrument = instrument
        self.volatility = volatility
        self.interest_rate = interest_rate
        self.lowest = lowest
        self.highest = highest
        self.step_ticks = step_ticks

    def document(self) -> dict:
        """Builds the `option_model` pricing object UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `option_model`, whose value holds the underlying as its `instrument_id`, `volatility`, and `interest_rate`, `lowest`, `highest` and `step_ticks` when each is set.

        Raises:
            Nothing.

        Examples:
            Print a rule that prices a Nifty option at 14% implied volatility off the index:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders.plan_parts import option_model_pricing

            index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pricing = option_model_pricing.OptionModelPricing(
                instrument=index,
                volatility=14.0,
            )
            print(pricing.document())
            ```

            Print a rule that grows the index at 6.5% a year to expiry and keeps the premium between 50 and 120:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders.plan_parts import option_model_pricing

            index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pricing = option_model_pricing.OptionModelPricing(
                instrument=index,
                volatility=12.5,
                interest_rate=6.5,
                lowest=50.0,
                highest=120.0,
                step_ticks=2,
            )
            print(pricing.document())
            ```
        """
        settings = {
            "instrument_id": self.instrument.instrument_id,
            "volatility": self.volatility,
        }
        if self.interest_rate is not None:
            settings["interest_rate"] = self.interest_rate
        if self.lowest is not None:
            settings["lowest"] = self.lowest
        if self.highest is not None:
            settings["highest"] = self.highest
        if self.step_ticks is not None:
            settings["step_ticks"] = self.step_ticks
        return {
            "option_model": settings,
        }
