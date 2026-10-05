"""Rest a bid whose filled part would be closed an hour from now.

The program places a time stop: a buy of one Vodafone Idea share 3% below the market, which UBI would cancel an hour from now, India time, before closing whatever had filled with a market sell. It closes only what this order filled, never anything else held in the share. The bid does not fill in the seconds the order lives; the program prints the parent and the resting bid and cancels it. It passes `hold_limits=False`, so UBI sends the order to the broker at once instead of holding it until the market reaches its price.

Typical usage example:

  .venv/bin/python examples/orders/time_stop/time_stop_order/bid_closed_in_an_hour.py
"""

import datetime
import time
import zoneinfo

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.assets import instruments
from tradingmachine.orders import time_stop
from tradingmachine.unified_broker_interface import exceptions


class BidClosedInAnHour:
    """An entry whose filled part is closed at a time of day, run by the order engine as a time stop.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account, used to read the engine's answer when it comes late.
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        order: The tradingmachine.orders.time_stop.TimeStopOrder the program places, or None before run() builds it.
    """

    def __init__(self):
        """Looks up the shares the program trades.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A share could not be found in UBI.
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

    def time_of_day_from_now(self, minutes: int) -> str:
        """Gives the India time of day a number of minutes from now, kept on today's date so that UBI never reads it as a time that has already passed.

        Args:
            minutes: The int number of minutes to add to the time now in India.

        Returns:
            The str time of day as `HH:MM:SS`, and 23:59:59 when the minutes would run past midnight.

        Raises:
            Nothing.
        """
        now = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
        later = now + datetime.timedelta(minutes=minutes)
        if later.date() != now.date():
            return "23:59:59"
        return later.strftime("%H:%M:%S")

    def build_order(self, dry_run: bool) -> time_stop.TimeStopOrder:
        """Builds a buy 3% below the market whose filled part is closed an hour from now.

        Args:
            dry_run: A bool that is True to build the order as a dry run, which UBI only checks and prices.

        Returns:
            The tradingmachine.orders.time_stop.TimeStopOrder, not yet placed.

        Raises:
            ValueError: UBI has no last price for a share.
        """
        return time_stop.TimeStopOrder(
            self.share,
            transaction_type="buy",
            product="mis",
            order_type="limit",
            quantity=1,
            price=self.price_from_market(self.share, -3),
            until_time=self.time_of_day_from_now(60),
            hold_limits=False,
            dry_run=dry_run,
        )

    def print_parent(self) -> None:
        """Prints the state the order engine holds the order in and each leg it has.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the parent.
        """
        parent = self.order.parent
        print(f"Parent state: {parent['state']}")
        for leg in parent["legs"]:
            print(
                f"  leg {leg.get('role')}: {leg.get('transaction_type')} "
                f"{leg.get('quantity')} at {leg.get('price')} "
                f"trigger {leg.get('trigger_price')}, {leg.get('state')}"
            )

    def print_broker_orders(self) -> None:
        """Prints the broker orders the order has placed so far.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the order book.
        """
        broker_orders = self.order.orders
        if broker_orders is None:
            print("No broker order has been placed yet.")
            return
        for row in broker_orders.to_dict("records"):
            print(
                f"  order {row.get('order_id')}: {row.get('transaction_type')} "
                f"{row.get('quantity')} at {row.get('price')}, {row.get('status')}"
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
        """Cancels the order in the order engine, with every leg it still has at a broker, and prints the result.

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
            for leg in answer["cancelled_legs"]:
                print(
                    f"  {leg.get('broker')} {leg.get('order_id')}: {leg.get('outcome')}"
                )
            if answer["state"] == "cancelled":
                return
            time.sleep(3)
        raise RuntimeError(
            f"Parent {self.order.parent_id} is still not cancelled, so check it by hand"
        )

    def run(self) -> None:
        """Places the time stop, prints the parent and the resting bid, then cancels it.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for a share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.order = self.build_order(dry_run=False)
        answer = self.place_order()
        print(
            f"Placed a {self.order.SYNTHETIC_TYPE} order: outcome "
            f"{answer.get('outcome')}, parent {self.order.parent_id}"
        )
        try:
            time.sleep(2)
            self.print_parent()
            self.print_broker_orders()
        finally:
            self.cancel_order()


if __name__ == "__main__":
    BidClosedInAnHour().run()
