"""Place a small batch of held orders, catching UnifiedBrokerInterfaceError and counting rate limits.

A program sending many orders at once may meet a broker's order limit, which arrives as RateLimitError with status code 429. The program places three buy limit orders for one IDEA share each, at about 3%, 4% and 5% below the last price, which UBI's order engine holds rather than sends. It catches the base class UnifiedBrokerInterfaceError for each, counts the refusals with status code 429 apart from any others, finds the parent of any order whose outcome is unknown (status code 504) through the engine's answer to its intent, and cancels every order that was accepted before it finishes.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/rate_limit_error/place_a_batch_and_count_refusals.py
"""

import decimal
import time

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class HeldOrderBatch:
    """A batch of held limit orders whose refusals are counted by kind.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the orders are for.
        trading_account: The tradingmachine.accounts.account.Account whose engine answers are read when an order's outcome is unknown.
        discounts: The list of str fractions below the last price to bid at.
        parent_ids: The list of str parent ids of the orders accepted.
        rate_limited_count: The int number of orders refused with HTTP 429.
        other_refusal_count: The int number of orders refused for another reason.
    """

    def __init__(self):
        """Creates the batch for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.trading_account = account.Account()
        self.discounts = [
            "0.03",
            "0.04",
            "0.05",
        ]
        self.parent_ids = []
        self.rate_limited_count = 0
        self.other_refusal_count = 0

    def limit_price(self, last_price: float, discount: str) -> float:
        """Works out a buy price a fraction below the last price, rounded down to the tick.

        Args:
            last_price: The float last price in rupees.
            discount: The str fraction to bid below it, such as `0.03`.

        Returns:
            The float limit price in rupees.

        Raises:
            Nothing.
        """
        factor = decimal.Decimal(1) - decimal.Decimal(discount)
        target = decimal.Decimal(str(last_price)) * factor
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

    def place_all(self) -> None:
        """Places every order in the batch, counting the refusals.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not give the last price.
        """
        last_price = self.share.last_price
        for discount in self.discounts:
            price = self.limit_price(last_price, discount)
            try:
                answer = self.share.buy_at_limit_price(
                    price=price,
                    quantity=1,
                    product="cnc",
                )
            except exceptions.UnifiedBrokerInterfaceError as error:
                if error.status_code == 504:
                    parent_id = self.parent_id_from_intent(
                        error.detail.get("intent_id")
                    )
                    if parent_id is not None:
                        self.parent_ids.append(parent_id)
                    print(f"Buy at {price}: outcome unknown, parent {parent_id}")
                    continue
                if error.status_code == 429:
                    self.rate_limited_count += 1
                else:
                    self.other_refusal_count += 1
                print(f"Buy at {price}: refused with {type(error).__name__}")
                continue
            self.parent_ids.append(answer["parent_id"])
            print(f"Buy at {price}: held as parent {answer['parent_id']}")

    def run(self) -> None:
        """Places the batch, prints the counts and cancels every accepted order.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a cancel.
        """
        try:
            self.place_all()
            print(f"Accepted: {len(self.parent_ids)}")
            print(f"Rate limited: {self.rate_limited_count}")
            print(f"Refused for another reason: {self.other_refusal_count}")
        finally:
            for parent_id in self.parent_ids:
                cancel_answer = self.share.cancel_parent(parent_id)
                print(f"Cancelled parent {parent_id}: {cancel_answer['state']}")


if __name__ == "__main__":
    HeldOrderBatch().run()
