"""Arm a trailing take-profit for a long that waits for a 5% rally before it places its stop.

A trailing stop protects a position, and UBI refuses it with HTTP 409 when no position is held on the side that opened it, so the program opens its own: it buys one Vodafone Idea share at the best offer as an intraday position. It then arms a trailing stop for that long with `activate_at` 5% above the market, so nothing is sent to a broker until the last price rises to that level, from where UBI would rest a sell stop 2% below the highest price seen. The level cannot be reached in the seconds the order lives, so the program prints the armed parent, cancels it and sells the share back. It refuses to start when Vodafone Idea is already held intraday, so that it never acts on a position it did not open.

Typical usage example:

  .venv/bin/python examples/orders/trailing_stop/trailing_stop_order/trailing_take_profit_on_a_long.py
"""

import time

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.assets import instruments
from tradingmachine.orders import trailing_stop
from tradingmachine.unified_broker_interface import exceptions


class LongTrailingTakeProfit:
    """A trailing stop for a long, armed as a take-profit that starts trailing after a 5% rally.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account, used to read the engine's answer when it comes late.
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        quantity_before: The int intraday quantity of Vodafone Idea held before the program opened its position.
        order: The tradingmachine.orders.trailing_stop.TrailingStopOrder the program places, or None before run() builds it.
    """

    def __init__(self):
        """Looks up the shares the program trades.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A share could not be found in UBI.
        """
        self.trading_account = account.Account()
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.quantity_before = 0
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

    def build_order(self, dry_run: bool) -> trailing_stop.TrailingStopOrder:
        """Builds a trailing stop for a long that activates 5% above the market and trails by 2%.

        Args:
            dry_run: A bool that is True to build the order as a dry run, which UBI only checks and prices.

        Returns:
            The tradingmachine.orders.trailing_stop.TrailingStopOrder, not yet placed.

        Raises:
            ValueError: UBI has no last price for a share.
        """
        return trailing_stop.TrailingStopOrder(
            self.share,
            transaction_type="buy",
            product="mis",
            order_type="limit",
            quantity=1,
            price=self.price_from_market(self.share, 0),
            trail_percent=2.0,
            stop_limit_offset=0.05,
            activate_at=self.price_from_market(self.share, 5),
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

    def held_quantity(self) -> int:
        """Gives the net intraday quantity of Vodafone Idea held now.

        Returns:
            The int quantity, positive when long, negative when short and 0 when nothing is held.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the positions.
        """
        positions = self.share.net_positions
        if positions is None:
            return 0
        total = 0
        for row in positions.to_dict("records"):
            if row["product"] == "intraday":
                total = total + int(row["quantity"])
        return total

    def open_position(self) -> None:
        """Buys one share at the best offer as an intraday position and waits until UBI reports it.

        The buy is a marketable limit half a percent above the best offer rather than a market order, because brokers refuse market orders sent through an API, and it is immediate-or-cancel so that nothing is left resting if it cannot fill at once. UBI chooses the broker for each order, so a buy one broker refuses is sent again up to four times, and a buy the engine answers late is not sent again but waited for.

        Returns:
            None.

        Raises:
            TimeoutError: The position did not appear within thirty seconds.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or could not be reached.
        """
        for attempt in range(4):
            try:
                answer = self.share.buy_at_marketable_price(
                    quantity=1,
                    product="mis",
                    validity="ioc",
                    buffer_percent=0.5,
                )
            except exceptions.OrderRejectedError as error:
                print(f"A broker refused the buy, so it is sent again: {error}")
                continue
            except exceptions.OrderOutcomeUnknownError:
                print("The engine answered the buy late, so the position is watched.")
                break
            print(f"Opened with marketable buy {answer.get('order_id')}")
            break
        for attempt in range(30):
            if self.held_quantity() > self.quantity_before:
                print(f"Now holding {self.held_quantity()} intraday")
                return
            time.sleep(1)
        raise TimeoutError("The buy did not show as a position within 30 seconds")

    def close_position(self) -> None:
        """Sells back the share this program bought, if the position shows that it was bought, trying up to five times.

        The sell is sent with `reduce_position`, whose quantity reference UBI sizes and routes against the broker that actually holds the position, so the account is left as it was found rather than long at one broker and short at another. It is a limit half a percent below the last price, because brokers refuse market orders sent through an API.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached.
        """
        for attempt in range(5):
            if self.held_quantity() <= self.quantity_before:
                print(f"Back to {self.held_quantity()} intraday, as before.")
                return
            try:
                answer = self.share.reduce_position(
                    quantity=1,
                    product="mis",
                    price=self.price_from_market(self.share, -0.5),
                )
            except exceptions.OrderRejectedError as error:
                print(f"A broker refused the sell, so it is sent again: {error}")
                time.sleep(2)
                continue
            except exceptions.OrderOutcomeUnknownError:
                print(
                    "The engine answered the sell late, so the position is read again."
                )
                time.sleep(10)
                continue
            print(f"Reducing the position with sell {answer.get('order_id')}")
            time.sleep(4)
        print("The position could still be open, so check it by hand.")

    def run(self) -> None:
        """Opens the position, arms the trailing stop, prints the parent, cancels it and closes the position.

        Returns:
            None.

        Raises:
            RuntimeError: Vodafone Idea was already held intraday, so the program does not touch it.
            ValueError: UBI has no last price for a share.
            TimeoutError: The opening order did not show as a position in time.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.quantity_before = self.held_quantity()
        if self.quantity_before != 0:
            raise RuntimeError(
                f"Vodafone Idea is already held intraday ({self.quantity_before}), so the program leaves that position alone"
            )
        try:
            self.open_position()
            self.order = self.build_order(dry_run=False)
            answer = self.place_order()
            print(
                f"Placed a {self.order.SYNTHETIC_TYPE} order: outcome "
                f"{answer.get('outcome')}, parent {self.order.parent_id}"
            )
            print(
                f"The stop is placed when the price reaches {answer.get('activate_at')}"
            )
            try:
                time.sleep(2)
                self.print_parent()
            finally:
                self.cancel_order()
        finally:
            self.close_position()


if __name__ == "__main__":
    LongTrailingTakeProfit().run()
