"""The `price_crosses` trigger of a plan: a price reaching a level.

With no direction, an order sent as a buy waits for the price to fall to the level and one sent as a sell for it to rise, which is market-if-touched's meaning for an entry and a stop's meaning for an order that protects a position. The price watched can be the order's own instrument or another one.

Typical usage example:

  condition = price_crosses.PriceCrosses(level=995.0, field="bid")
  document = condition.document()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders.plan_parts import plan_part


class PriceCrosses(plan_part.PlanPart):
    """A condition that holds once a price reaches a level from the side that fires.

    Attributes:
        level: The float level in rupees.
        direction: The str direction, `at_or_above` or `at_or_below`, or None to take it from the order's side.
        field: The str price watched, such as `last`, `bid`, `ask` or `mid`, or None for `last`.
        instrument: The instruments.Instrument watched, or None for the order's own instrument.
        confirm: The str confirmation, `none`, `double_last` or `held`, or None for `none`.
        hold_seconds: The int seconds the price must stay past the level under `held`, or None.
    """

    def __init__(
        self,
        *,
        level: float,
        direction: str | None = None,
        field: str | None = None,
        instrument: instruments.Instrument | None = None,
        confirm: str | None = None,
        hold_seconds: int | None = None,
    ):
        """Initialises the condition with its level and settings.

        Args:
            level: The float level in rupees.
            direction: The str direction, `at_or_above` or `at_or_below`, or None for a buy to wait for a fall and a sell for a rise.
            field: The str price watched, `last`, `bid`, `ask`, `mid`, `average_price`, `previous_close` or `opposite_touch`, or None for `last`.
            instrument: The instruments.Instrument to watch, or None to watch the order's own instrument.
            confirm: The str confirmation, `none`, `double_last` for two last prices in a row past the level, or `held` for the price to stay past it for `hold_seconds`, or None for `none`.
            hold_seconds: The int seconds the price must stay past the level, required with `held`, or None.

        Raises:
            Nothing.
        """
        self.level = level
        self.direction = direction
        self.field = field
        self.instrument = instrument
        self.confirm = confirm
        self.hold_seconds = hold_seconds

    def document(self) -> dict:
        """Builds the `price_crosses` condition UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `price_crosses`, whose value holds `level` and each other setting that is set, with the watched instrument as its `instrument_id`.

        Raises:
            Nothing.

        Examples:
            Print a condition on the order's own last price, with the direction taken from its side:

            ```python
            from tradingmachine.orders.plan_parts import price_crosses

            condition = price_crosses.PriceCrosses(level=995.0)
            print(condition.document())
            ```

            Print a condition on the bid that must stay at or above the level for ten seconds:

            ```python
            from tradingmachine.orders.plan_parts import price_crosses

            condition = price_crosses.PriceCrosses(
                level=1010.0,
                direction="at_or_above",
                field="bid",
                confirm="held",
                hold_seconds=10,
            )
            print(condition.document())
            ```

            Print a condition that watches another instrument, the Nifty 50 index:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders.plan_parts import price_crosses

            index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            condition = price_crosses.PriceCrosses(
                level=25000.0,
                direction="at_or_above",
                instrument=index,
            )
            print(condition.document())
            ```
        """
        settings = {
            "level": self.level,
        }
        if self.direction is not None:
            settings["direction"] = self.direction
        if self.field is not None:
            settings["field"] = self.field
        if self.instrument is not None:
            settings["instrument_id"] = self.instrument.instrument_id
        if self.confirm is not None:
            settings["confirm"] = self.confirm
        if self.hold_seconds is not None:
            settings["hold_seconds"] = self.hold_seconds
        return {
            "price_crosses": settings,
        }
