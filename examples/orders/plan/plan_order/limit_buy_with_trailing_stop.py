"""Preview and rest a limit buy whose every fill is protected by a trailing stop, built as a plan.

The program builds a plan of two parts joined with `then`: a buy of one Vodafone Idea share 3% below the market, and a stop that protects whatever it buys and trails 2% behind the market. It previews the plan with a dry run, then places it, prints each part's state and cancels it before anything fills.

Typical usage example:

  .venv/bin/python examples/orders/plan/plan_order/limit_buy_with_trailing_stop.py
"""

import time

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.assets import instruments
from tradingmachine.orders import plan
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import trail_pricing
from tradingmachine.unified_broker_interface import exceptions


class LimitBuyWithTrailingStop:
    """A limit buy followed by a trailing stop sized to each of its fills, run as a plan.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account, used to read the engine's answer when it comes late.
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        order: The tradingmachine.orders.plan.PlanOrder the program places, or None before run() builds it.
    """

    def __init__(self):
        """Looks up the share the program trades.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.trading_account = account.Account()
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.order = None

    def price_from_market(
        self,
        instrument: instruments.TradeableInstrument,
        percent: float,
    ) -> float:
        """Gives a price a percentage away from an instrument's last price, rounded to its tick size.

        Args:
            instrument: The tradingmachine.assets.instruments.TradeableInstrument to price.
            percent: The float percentage to move from the last price, negative for a price below the market.

        Returns:
            The float price in rupees.

        Raises:
            ValueError: UBI has no last price for the instrument.
        """
        last_price = instrument.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {instrument!r}")
        tick_size = 0.05
        if instrument.tick_size is not None:
            tick_size = float(instrument.tick_size)
        ticks = round(last_price * (1 + percent / 100) / tick_size)
        return round(ticks * tick_size, 2)

    def build_order(self, dry_run: bool) -> plan.PlanOrder:
        """Builds a buy 3% below the market, then a stop trailing 2% behind each fill.

        Args:
            dry_run: A bool that is True to build the order as a dry run, which UBI only checks and prices.

        Returns:
            The tradingmachine.orders.plan.PlanOrder, not yet placed.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        trailing_stop = order_part.OrderPart(
            side="protect",
            pricing=trail_pricing.TrailPricing(
                percent=2.0,
                limit_offset=0.05,
            ),
        )
        return plan.PlanOrder(
            self.share,
            transaction_type="buy",
            product="mis",
            order_type="limit",
            quantity=1,
            price=self.price_from_market(self.share, -3),
            plan=then_part.ThenPart(
                first=order_part.OrderPart(),
                each_fill=trailing_stop,
            ),
            dry_run=dry_run,
        )

    def preview(self) -> None:
        """Sends the plan as a dry run and prints the broker request and the plan as UBI would run it.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the plan or could not be reached.
        """
        answer = self.build_order(dry_run=True).place()
        print("Dry run of the plan:")
        print(f"  first broker request: {answer.get('request')}")
        print(f"  plan as it would run: {answer.get('plan')}")

    def print_parent(self) -> None:
        """Prints the state the order engine holds the plan in and the state of each of its parts.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the parent.
        """
        parent = self.order.parent
        print(f"Parent state: {parent['state']}")
        parts = parent.get("parameters", {}).get("parts", {})
        for path, part in parts.items():
            print(f"  part {path}: {part.get('state')}, target {part.get('target')}")
        for leg in parent.get("legs", []):
            print(
                f"  leg {leg.get('role')}: {leg.get('transaction_type')} "
                f"{leg.get('quantity')} at {leg.get('price')}, {leg.get('state')}"
            )

    def place_order(self) -> dict:
        """Places the order, sending it again when a broker refuses it, and reading the engine's stored answer when the engine answers too late, so that the order can always be cancelled.

        Returns:
            The dict answer of the placement, whose `parent_id` is also kept on the order.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.OrderRejectedError: Brokers refused the order three times.
            tradingmachine.unified_broker_interface.exceptions.OrderOutcomeUnknownError: The engine's answer could not be read within thirty seconds.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or could not be reached.
        """
        for attempt in range(3):
            try:
                return self.order.place()
            except exceptions.OrderRejectedError as error:
                if attempt == 2:
                    raise
                print(f"A broker refused the order, so it is sent again: {error}")
                time.sleep(1)
            except exceptions.OrderOutcomeUnknownError as error:
                return self.read_late_answer(error)
        return {}

    def read_late_answer(
        self,
        error: exceptions.OrderOutcomeUnknownError,
    ) -> dict:
        """Reads the order engine's stored answer to a placement it answered too late, and keeps its parent id.

        Args:
            error: The tradingmachine.unified_broker_interface.exceptions.OrderOutcomeUnknownError the placement raised.

        Returns:
            The dict answer the placement would have given.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.OrderOutcomeUnknownError: The engine's answer could not be read within thirty seconds.
        """
        intent_id = error.detail.get("intent_id")
        print(f"The engine answered late, so intent {intent_id} is read.")
        for attempt in range(15):
            time.sleep(2)
            try:
                stored = self.trading_account.intent(intent_id)
            except exceptions.NotFoundError:
                continue
            answer = stored["response"]
            self.order.parent_id = answer.get("parent_id")
            return answer
        raise error

    def cancel_order(self) -> None:
        """Cancels the plan in the order engine, with every leg it still has at a broker, and prints the result.

        A broker can refuse or be slow to answer one leg's cancel, which leaves the parent `cancelling`, and the engine itself can answer late, so the cancel is sent again until the parent is `cancelled`, up to five times.

        Returns:
            None.

        Raises:
            RuntimeError: The parent was still not cancelled after five attempts, so a leg may still be live.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the cancel or could not be reached.
        """
        if self.order is None or self.order.parent_id is None:
            print("No order was placed, so there is nothing to cancel.")
            return
        for attempt in range(5):
            try:
                answer = self.order.cancel()
            except exceptions.ConflictError:
                print(f"The parent has already finished: {self.order.parent['state']}")
                return
            except exceptions.OrderOutcomeUnknownError:
                print("The engine answered the cancel late, so it is sent again.")
                time.sleep(3)
                continue
            print(
                f"Cancelled: state {answer['state']}, "
                f"{len(answer['cancelled_legs'])} legs cancelled"
            )
            if answer["state"] == "cancelled":
                return
            time.sleep(3)
        raise RuntimeError(
            f"Parent {self.order.parent_id} is still not cancelled, so check it by hand"
        )

    def run(self) -> None:
        """Previews the plan, places it, prints its parts, then cancels it.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.preview()
        self.order = self.build_order(dry_run=False)
        answer = self.place_order()
        print(
            f"Placed a {self.order.SYNTHETIC_TYPE} order: outcome "
            f"{answer.get('outcome')}, parent {self.order.parent_id}"
        )
        try:
            time.sleep(2)
            self.print_parent()
        finally:
            self.cancel_order()


if __name__ == "__main__":
    LimitBuyWithTrailingStop().run()
