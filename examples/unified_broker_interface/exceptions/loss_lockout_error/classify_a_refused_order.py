"""Place an order and sort any refusal by its status code, catching UnifiedBrokerInterfaceError.

A trading program needs to tell a lockout, which ends the day's trading, from refusals that call for fixing the order or retrying. The program places a buy limit order for one IDEA share about 3% below the last price, which UBI's order engine holds rather than sends, and catches the base class UnifiedBrokerInterfaceError so that a LossLockoutError, recognised by its status code 403, is told apart from every other refusal. The order is cancelled at once if it was accepted, including when its outcome was unknown and the engine's answer to its intent shows it was held.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/loss_lockout_error/classify_a_refused_order.py
"""

import decimal
import time

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class RefusalClassifier:
    """A held limit order whose refusal, if any, is sorted by what to do next.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
        trading_account: The tradingmachine.accounts.account.Account whose engine answers are read when the order's outcome is unknown.
        advice_for_status_code: The dict of int status code to str advice for a refused order.
    """

    def __init__(self):
        """Creates the order's setting for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.trading_account = account.Account()
        self.advice_for_status_code = {
            400: "fix the order and send it again",
            403: "stop trading for the day, because the loss limit is reached",
            422: "read the broker's reason in the order document",
            429: "wait and retry, because the broker is at its order limit",
            503: "check that the order engine is running",
            504: "do not resend, because the order may be working; read the engine's answer to its intent",
        }

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

    def parent_id_from_intent(self, intent_id: str | None) -> str | None:
        """Finds the parent an order with an unknown outcome became, by reading the engine's answer to its intent.

        Args:
            intent_id: The str intent id from the error's detail, or None when the detail has none.

        Returns:
            The str parent id the engine gave the order, or None when it gave none or did not answer within ten seconds.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than an answer not being stored yet.
        """
        if intent_id is None:
            return None
        for attempt in range(10):
            try:
                answer = self.trading_account.intent(intent_id)
            except exceptions.NotFoundError:
                print(f"No answer to the intent yet after {attempt} seconds.")
                time.sleep(1)
                continue
            return answer["response"].get("parent_id")
        return None

    def run(self) -> None:
        """Places the order, prints the advice for any refusal, and cancels an accepted order.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the cancel.
        """
        try:
            answer = self.share.buy_at_limit_price(
                price=self.limit_price(),
                quantity=1,
                product="cnc",
            )
        except exceptions.UnifiedBrokerInterfaceError as error:
            advice = self.advice_for_status_code.get(
                error.status_code,
                "report the failure",
            )
            print(
                f"Refused with {type(error).__name__} ({error.status_code}): {advice}"
            )
            if error.status_code != 504:
                return
            parent_id = self.parent_id_from_intent(error.detail.get("intent_id"))
            if parent_id is not None:
                cancel_answer = self.share.cancel_parent(parent_id)
                print(f"Cancelled parent {parent_id}: {cancel_answer['state']}")
            return
        parent_id = answer["parent_id"]
        try:
            print(
                f"Accepted: outcome {answer['outcome']}, so there is no lockout today."
            )
        finally:
            cancel_answer = self.share.cancel_parent(parent_id)
            print(f"Cancelled parent {parent_id}: {cancel_answer['state']}")


if __name__ == "__main__":
    RefusalClassifier().run()
