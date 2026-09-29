"""Place an order and refuse to resend it when its outcome is unknown, catching UnifiedBrokerInterfaceError.

A refused order can be fixed and sent again, but an order whose outcome is unknown, reported as OrderOutcomeUnknownError with status code 504, may already be working, and sending it again could double the position. The program places a buy limit order for one IDEA share about 3% below the last price, which UBI's order engine holds rather than sends, catches the base class UnifiedBrokerInterfaceError, and checks the account's open parents instead of resending when the status code is 504. The order is cancelled at once if it was accepted.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/order_outcome_unknown_error/never_resend_an_unknown_order.py
"""

import decimal

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class CarefulPlacement:
    """A held limit order that is never sent twice.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
        trading_account: The tradingmachine.accounts.account.Account whose open parents are checked.
    """

    def __init__(self):
        """Creates the order's setting for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.trading_account = account.Account()

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

    def run(self) -> None:
        """Places the order, reports an unknown outcome without resending, and cancels an accepted order.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order for a reason other than an unknown outcome, or refused the cancel.
        """
        try:
            answer = self.share.buy_at_limit_price(
                price=self.limit_price(),
                quantity=1,
                product="cnc",
            )
        except exceptions.UnifiedBrokerInterfaceError as error:
            if error.status_code != 504:
                raise
            print(
                f"{type(error).__name__}: the order may be working, so it is not sent again."
            )
            print(f"Open parents now: {self.trading_account.parents}")
            return
        parent_id = answer["parent_id"]
        try:
            print(f"The outcome is known: {answer['outcome']}, parent {parent_id}")
        finally:
            cancel_answer = self.share.cancel_parent(parent_id)
            print(f"Cancelled: {cancel_answer['state']}")


if __name__ == "__main__":
    CarefulPlacement().run()
