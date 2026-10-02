"""Rest a bid for one lot of the at-the-money Nifty call at 5% implied volatility, priced off the index.

The program finds the Nifty call nearest the index on the nearest expiry and places a volatility order to buy one lot. UBI prices the bid with the Black-76 model at 5% implied volatility, growing the index at 6.5% a year to expiry, and never pays more than half the call's last price, so the bid sits at least half below the market; it is also kept no lower than 40% of the last price. The bid cannot fill in the seconds it lives; the program prints the parent and its order at the broker and cancels it.

Typical usage example:

  .venv/bin/python examples/orders/volatility/volatility_order/call_bid_at_a_low_volatility.py
"""

import time

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.assets import instruments
from tradingmachine.orders import volatility
from tradingmachine.unified_broker_interface import exceptions


class CallBidAtALowVolatility:
    """A bid for one lot of the at-the-money Nifty call, priced at 5% implied volatility off the index.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account, used to read the engine's answer when it comes late.
        index: The tradingmachine.assets.equities.EquityIndex for the Nifty 50 on the NSE, the forward the model prices from.
        option: The tradingmachine.assets.equities.EquityIndexOption call nearest the index on the nearest expiry.
        order: The tradingmachine.orders.volatility.VolatilityOrder the program places, or None before run() builds it.
    """

    def __init__(self):
        """Looks up the index and the call nearest to it on the nearest expiry.

        Raises:
            ValueError: UBI has no last price for the index, or no call on its nearest expiry.
            tradingmachine.assets.exceptions.InstrumentError: The index or the option could not be found in UBI.
        """
        self.trading_account = account.Account()
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        index_price = self.index.last_price
        if index_price is None:
            raise ValueError(f"UBI has no last price for {self.index!r}")
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        chain = equities.EquityIndexOption.chain(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[0],
        )
        calls = chain[chain["option_type"] == "CE"]
        nearest_strike = None
        nearest_distance = None
        for strike_price in calls["strike_price"]:
            distance = abs(strike_price - index_price)
            if nearest_distance is None or distance < nearest_distance:
                nearest_strike = strike_price
                nearest_distance = distance
        if nearest_strike is None:
            raise ValueError(f"UBI has no Nifty call expiring on {expiries[0]}")
        self.option = equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[0],
            strike_price=nearest_strike,
            option_type="CE",
            underlying=self.index,
        )
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

    def build_order(self, dry_run: bool) -> volatility.VolatilityOrder:
        """Builds a buy of one lot priced at 5% volatility, paying at most half the last price and no less than 40% of it.

        Args:
            dry_run: A bool that is True to build the order as a dry run, which UBI only checks and prices.

        Returns:
            The tradingmachine.orders.volatility.VolatilityOrder, not yet placed.

        Raises:
            ValueError: UBI has no last price for the option.
        """
        return volatility.VolatilityOrder(
            self.option,
            transaction_type="buy",
            product="mis",
            order_type="limit",
            quantity=int(self.option.lot_size),
            price=self.price_from_market(self.option, -50),
            watch_instrument=self.index,
            volatility=5.0,
            interest_rate=6.5,
            lowest_price=self.price_from_market(self.option, -60),
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
        """Places the bid, prints the parent and its order at the broker, then cancels it.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.order = self.build_order(dry_run=False)
        answer = self.place_order()
        print(
            f"Placed a {self.order.SYNTHETIC_TYPE} order: outcome "
            f"{answer.get('outcome')}, parent {self.order.parent_id}"
        )
        print(f"The call was first bid at {answer.get('priced_at')}")
        try:
            time.sleep(2)
            self.print_parent()
            self.print_broker_orders()
        finally:
            self.cancel_order()


if __name__ == "__main__":
    CallBidAtALowVolatility().run()
