"""The `pre_open` venue of a plan: an order sent in the pre-open session so it trades at the opening auction's price.

UBI sends the order at `at_time`, 09:00:30 by default, through a `time_from` trigger of its own, so an order with this venue takes no trigger (`pre_open_sets_its_time`). The pre-open takes only `LIMIT` and `MARKET` orders, on NSE and BSE cash until 09:10, market orders until 09:05, and on NSE stock and index futures until 09:07; anything else, or an order sent after collection has closed, is refused with HTTP 400. Unlike most parts, a venue is an entry of the order's `venue` list rather than a one-key object.

Typical usage example:

  part = order_part.OrderPart(venue=pre_open_venue.PreOpenVenue(at_time="09:02"))
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class PreOpenVenue(plan_part.PlanPart):
    """The pre-open session, with the time the order is sent into it.

    Attributes:
        at_time: The str time of day the order is sent, such as `09:02`, or None for UBI's default of `09:00:30`.
    """

    def __init__(
        self,
        *,
        at_time: str | None = None,
    ):
        """Initialises the venue with the time the order is sent.

        Args:
            at_time: The str time of day in India while the pre-open takes orders, such as `09:02` or `09:00:30`, or None for UBI's default of `09:00:30`.

        Raises:
            Nothing.
        """
        self.at_time = at_time

    def document(self) -> dict:
        """Builds the venue entry UBI reads.

        Returns:
            A dict holding `session` set to `pre_open`, and `at_time` when it is not None. `OrderPart` puts it in a list of one under `venue`.

        Raises:
            Nothing.

        Examples:
            Print the venue entry at UBI's default time:

            ```python
            from tradingmachine.orders.plan_parts import pre_open_venue

            print(pre_open_venue.PreOpenVenue().document())
            ```

            Print a limit buy at 1000 sent into the pre-open at two minutes past nine:

            ```python
            from tradingmachine.orders.plan_parts import fixed_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import pre_open_venue

            part = order_part.OrderPart(
                pricing=fixed_pricing.FixedPricing(price=1000.0, order_type="LIMIT"),
                venue=pre_open_venue.PreOpenVenue(at_time="09:02"),
            )
            print(part.document())
            ```
        """
        entry = {
            "session": "pre_open",
        }
        if self.at_time is not None:
            entry["at_time"] = self.at_time
        return entry
