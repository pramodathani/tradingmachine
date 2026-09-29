"""Place an order that is retried once when UBI raises RateLimitError.

When the broker chosen for an order is at its order limit, or has used its daily order cap, UBI answers HTTP 429 and the client raises RateLimitError. The program places a buy limit order for one IDEA share about 3% below the last price, which UBI's order engine holds rather than sends, waits two seconds and tries once more if it is rate limited, and cancels the order at once.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/rate_limit_error/retry_once_after_a_rate_limit.py
"""

import decimal
import time

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class RateLimitedOrder:
    """A held limit order that waits and retries once when rate limited.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
        retry_wait_seconds: The float number of seconds to wait before the retry.
    """

    def __init__(self):
        """Creates the order's setting for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.retry_wait_seconds = 2.0

    def limit_price(self) -> float:
        """Works out a buy price about 3% below the last price, rounded down to the tick.

        Returns:
            The float limit price in rupees.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not give the last price.
        """
        target = decimal.Decimal(str(self.share.last_price)) * decimal.Decimal("0.97")
        ticks = (target / self.share.tick_size).to_integral_value(
            rounding=decimal.ROUND_FLOOR
        )
        return float(ticks * self.share.tick_size)

    def place(self) -> dict:
        """Places the held order once.

        Returns:
            The dict UBI answered the placement with.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order.
        """
        return self.share.buy_at_limit_price(
            price=self.limit_price(),
            quantity=1,
            product="cnc",
        )

    def place_with_one_retry(self) -> dict:
        """Places the held order, waiting and retrying once when rate limited.

        Returns:
            The dict UBI answered the placement with.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.RateLimitError: The retry was rate limited too.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order for another reason.
        """
        try:
            return self.place()
        except exceptions.RateLimitError as error:
            print(
                f"RateLimitError: {error.message}; retrying in {self.retry_wait_seconds} seconds"
            )
        time.sleep(self.retry_wait_seconds)
        return self.place()

    def run(self) -> None:
        """Places the order and cancels it at once.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or the cancel.
        """
        answer = self.place_with_one_retry()
        parent_id = answer["parent_id"]
        try:
            print(f"Placed without hitting a rate limit: parent {parent_id}")
        finally:
            cancel_answer = self.share.cancel_parent(parent_id)
            print(f"Cancelled: {cancel_answer['state']}")


if __name__ == "__main__":
    RateLimitedOrder().run()
