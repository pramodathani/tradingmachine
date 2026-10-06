"""Buy one share with a marketable limit that takes no buffer and gives up after ten seconds, then sell it back.

The program previews, then places, a marketable limit to buy one Vodafone Idea share intraday at the best offer itself, with no ticks of buffer, which UBI moves after the offer until it fills and cancels after ten seconds if it has not. It prints the parent as it ends and the price the buy filled at, and sells the share back.

Typical usage example:

  .venv/bin/python examples/orders/marketable_limit/marketable_limit_order/buy_at_the_offer_for_ten_seconds.py
"""

import time

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.assets import instruments
from tradingmachine.orders import marketable_limit
from tradingmachine.unified_broker_interface import exceptions


class BuyAtTheOffer:
    """A one-share intraday buy sent as a limit at the best offer that follows the offer for ten seconds.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account, used to read the engine's answer when it comes late.
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        quantity_before: The int intraday quantity of Vodafone Idea held before the program bought its share.
        order: The tradingmachine.orders.marketable_limit.MarketableLimitOrder the program places, or None before run() builds it.
    """

    def __init__(self):
        """Looks up the share the program trades.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
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

    def build_order(
        self,
        dry_run: bool,
    ) -> marketable_limit.MarketableLimitOrder:
        """Builds a one-share market buy sent as a limit at the best offer for ten seconds.

        Args:
            dry_run: A bool that is True to build the order as a dry run, which UBI only checks and plans.

        Returns:
            The tradingmachine.orders.marketable_limit.MarketableLimitOrder, not yet placed.

        Raises:
            Nothing.
        """
        return marketable_limit.MarketableLimitOrder(
            self.share,
            transaction_type="buy",
            product="mis",
            order_type="market",
            quantity=1,
            buffer_ticks=0,
            fill_within_seconds=10,
            dry_run=dry_run,
        )

    def place_order(self) -> dict | None:
        """Places the order, reading the engine's stored answer when the engine answers too late.

        A refusal with HTTP 409 means the order could not be priced, because nobody was offering the share or no fresh quote had arrived, and nothing was sent.

        Returns:
            The dict answer of the placement, whose `parent_id` is also kept on the order, or None when UBI refused to price it.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.OrderOutcomeUnknownError: The engine's answer could not be read within thirty seconds.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or could not be reached.
        """
        try:
            return self.order.place()
        except exceptions.ConflictError as error:
            print(f"UBI could not price the buy, so nothing was sent: {error}")
            return None
        except exceptions.OrderOutcomeUnknownError as error:
            return self.read_late_answer(error)

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

    def wait_for_parent(self) -> None:
        """Waits up to twenty seconds for the parent to end, then prints its state and each leg.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the parent.
        """
        parent = self.order.parent
        for attempt in range(20):
            if parent["state"] in ("completed", "cancelled", "rejected", "failed"):
                break
            time.sleep(1)
            parent = self.order.parent
        print(f"Parent state: {parent['state']}")
        for leg in parent["legs"]:
            print(
                f"  leg {leg.get('role')}: {leg.get('transaction_type')} "
                f"{leg.get('quantity')} at {leg.get('price')}, {leg.get('state')}, "
                f"filled {leg.get('filled_quantity')} at {leg.get('average_price')}"
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
        """Previews the buy, places it, waits for it to end, and sells back whatever it bought.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        preview = self.build_order(dry_run=True).place()
        pricing = preview["plan"]["order"]["slots"]["pricing"]
        lifetime = preview["plan"]["order"]["slots"]["lifetime"]
        print(f"A dry run says UBI would price the buy with {pricing}")
        print(f"and end it with {lifetime}")
        self.quantity_before = self.held_quantity()
        self.order = self.build_order(dry_run=False)
        try:
            answer = self.place_order()
            if answer is None:
                return
            print(
                f"Placed a {self.order.SYNTHETIC_TYPE} order: outcome "
                f"{answer.get('outcome')}, parent {self.order.parent_id}"
            )
            self.wait_for_parent()
        finally:
            self.close_position()


if __name__ == "__main__":
    BuyAtTheOffer().run()
