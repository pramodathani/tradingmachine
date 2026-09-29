"""Place an order with handling for the OrderOutcomeUnknownError UBI raises when the engine does not answer in time.

An OrderOutcomeUnknownError means the order may or may not have been placed, so it must never simply be sent again. Its detail carries the `intent_id`, and the account's `intent` method reads the engine's answer once it arrives. The program places a buy limit order for one IDEA share about 3% below the last price, which UBI's order engine holds rather than sends; if the outcome is unknown it waits for the engine's answer through the intent, and in every case it cancels the held order at once.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/order_outcome_unknown_error/resolve_an_unknown_outcome_through_the_intent.py
"""

import decimal
import time

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class UnknownOutcomeResolution:
    """A held limit order whose unknown outcome is resolved through the engine's intent.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
        trading_account: The tradingmachine.accounts.account.Account the intent is read through.
        intent_wait_seconds: The int number of seconds to wait for the engine's answer.
    """

    def __init__(self):
        """Creates the order's setting for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.trading_account = account.Account()
        self.intent_wait_seconds = 30

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

    def wait_for_intent(self, intent_id: str) -> dict | None:
        """Reads the engine's answer to an intent, waiting a second between tries.

        Args:
            intent_id: The str intent id from the error's detail.

        Returns:
            The dict the placement would have answered with, or None when the engine has not answered in time.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than an answer not being stored yet.
        """
        for attempt in range(self.intent_wait_seconds):
            try:
                return self.trading_account.intent(intent_id)["response"]
            except exceptions.NotFoundError:
                print(f"No answer yet after {attempt} seconds.")
            time.sleep(1)
        return None

    def place(self) -> dict | None:
        """Places the held order and resolves an unknown outcome.

        Returns:
            The dict answer of the placement, or None when its outcome stayed unknown.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order.
        """
        try:
            return self.share.buy_at_limit_price(
                price=self.limit_price(),
                quantity=1,
                product="cnc",
            )
        except exceptions.OrderOutcomeUnknownError as error:
            print(f"OrderOutcomeUnknownError: {error.message}")
            return self.wait_for_intent(error.detail["intent_id"])

    def run(self) -> None:
        """Places the order and cancels it at once.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or the cancel.
        """
        answer = self.place()
        if answer is None:
            print(
                "The outcome is still unknown; check the account's parents before sending anything again."
            )
            return
        parent_id = answer.get("parent_id")
        try:
            print(f"Outcome {answer['outcome']}, parent {parent_id}")
        finally:
            if parent_id is not None:
                cancel_answer = self.share.cancel_parent(parent_id)
                print(f"Cancelled: {cancel_answer['state']}")


if __name__ == "__main__":
    UnknownOutcomeResolution().run()
