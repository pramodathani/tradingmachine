"""One instrument whose position counts towards the exposure an `ExposureHedgeOrder` keeps inside a band.

Typical usage example:

  watch = exposure_watch.ExposureWatch(nifty_call, exposure_per_unit=0.5)
  document = watch.document()
"""

from tradingmachine.assets import instruments


class ExposureWatch:
    """One watched instrument and how much exposure each unit of its position carries.

    Attributes:
        instrument: The instruments.Instrument whose net position is counted.
        exposure_per_unit: The float exposure one unit of the position carries, or None to let UBI count 1.
    """

    def __init__(
        self,
        instrument: instruments.Instrument,
        exposure_per_unit: float | None = None,
    ):
        """Initialises the watch.

        Args:
            instrument: The instruments.Instrument whose net position is counted.
            exposure_per_unit: The float exposure one unit carries, such as an option's delta, or None to let UBI count 1.

        Raises:
            Nothing.
        """
        self.instrument = instrument
        self.exposure_per_unit = exposure_per_unit

    def document(self) -> dict:
        """Builds the watched object UBI reads.

        Returns:
            A dict with `instrument_id`, and `exposure_per_unit` when it is set.

        Raises:
            Nothing.

        Examples:
            Print the watched object for a share, whose units each count as one:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import exposure_watch

            share = equities.Equity(exchange="nse", symbol="IDEA")
            watch = exposure_watch.ExposureWatch(share)
            print(watch.document())
            ```

            Build watched objects that weight two shares differently, as a beta would:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import exposure_watch

            first_share = equities.Equity(exchange="nse", symbol="IDEA")
            second_share = equities.Equity(exchange="nse", symbol="YESBANK")
            watches = [
                exposure_watch.ExposureWatch(first_share, exposure_per_unit=1.2),
                exposure_watch.ExposureWatch(second_share, exposure_per_unit=0.8),
            ]
            for watch in watches:
                print(watch.document())
            ```
        """
        watched = {
            "instrument_id": self.instrument.instrument_id,
        }
        if self.exposure_per_unit is not None:
            watched["exposure_per_unit"] = self.exposure_per_unit
        return watched
