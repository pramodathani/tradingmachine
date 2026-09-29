"""Place an order with handling for the LossLockoutError UBI raises once the day's loss limit is passed.

When the day's loss is past UBI's daily loss limit, the order engine refuses every new order with HTTP 403 and the client raises LossLockoutError. A trading program should then stop sending orders for the day rather than retry. The program places a buy limit order for one IDEA share about 3% below the last price, which the engine holds rather than sends, handles a lockout if there is one, and cancels the order at once.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/loss_lockout_error/stop_trading_when_locked_out.py
"""

import decimal

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class LockoutAwareOrder:
    """A held limit order that stops trading for the day when UBI reports a loss lockout.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
        trading_stopped: A bool that is True once a lockout has been seen.
    """

    def __init__(self):
        """Creates the order's setting for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.trading_stopped = False

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

    def place(self) -> dict | None:
        """Places the held order, or stops trading when UBI reports a lockout.

        Returns:
            The dict UBI answered the placement with, or None when the account is locked out.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order for a reason other than a lockout.
        """
        try:
            return self.share.buy_at_limit_price(
                price=self.limit_price(),
                quantity=1,
                product="cnc",
            )
        except exceptions.LossLockoutError as error:
            self.trading_stopped = True
            print(f"LossLockoutError: {error.message}")
            print("The daily loss limit is reached, so no more orders are sent today.")
            return None

    def run(self) -> None:
        """Places the order and cancels it at once.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or the cancel.
        """
        answer = self.place()
        if answer is None:
            return
        parent_id = answer["parent_id"]
        try:
            print(
                f"No lockout: the engine is holding parent {parent_id}, outcome {answer['outcome']}"
            )
        finally:
            cancel_answer = self.share.cancel_parent(parent_id)
            print(f"Cancelled: {cancel_answer['state']}")


if __name__ == "__main__":
    LockoutAwareOrder().run()
