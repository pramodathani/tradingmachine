"""Preview and start a hedge watching two shares weighted as a beta would weight them.

The program previews, then starts, an exposure hedge in Vodafone Idea that adds up the positions in Vodafone Idea and Yes Bank, weighting them 1 and 1.5, and trades only if the total moves more than 100 away from what it is now, so no hedge is traded; the program prints the parent and cancels it.

Typical usage example:

  .venv/bin/python examples/orders/exposure_hedge/exposure_hedge_order/weighted_two_share_exposure.py
"""

import time

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.assets import instruments
from tradingmachine.orders import exposure_hedge
from tradingmachine.orders import exposure_watch
from tradingmachine.unified_broker_interface import exceptions


class WeightedExposureHedge:
    """A hedge that keeps the weighted exposure of two shares inside a wide band.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account, used to read the engine's answer when it comes late.
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        second_share: The tradingmachine.assets.equities.Equity for Yes Bank on the NSE.
        order: The tradingmachine.orders.exposure_hedge.ExposureHedgeOrder the program places, or None before run() builds it.
    """

    def __init__(self):
        """Looks up the shares the program trades.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A share could not be found in UBI.
        """
        self.trading_account = account.Account()
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.second_share = equities.Equity(exchange="nse", symbol="YESBANK")
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

    def build_order(self, dry_run: bool) -> exposure_hedge.ExposureHedgeOrder:
        """Builds a hedge in Vodafone Idea over two weighted watched shares, with a band 100 either side of the exposure held now.

        Args:
            dry_run: A bool that is True to build the order as a dry run, which UBI only checks and prices.

        Returns:
            The tradingmachine.orders.exposure_hedge.ExposureHedgeOrder, not yet placed.

        Raises:
            ValueError: UBI has no last price for a share.
        """
        exposure = self.net_quantity(self.share) + 1.5 * self.net_quantity(
            self.second_share
        )
        return exposure_hedge.ExposureHedgeOrder(
            self.share,
            watched=[
                exposure_watch.ExposureWatch(self.share, exposure_per_unit=1.0),
                exposure_watch.ExposureWatch(self.second_share, exposure_per_unit=1.5),
            ],
            lower_band=exposure - 100,
            upper_band=exposure + 100,
            product="mis",
            hedge_exposure_per_unit=1.0,
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

    def net_quantity(self, instrument: instruments.TradeableInstrument) -> int:
        """Adds up the net quantity held in an instrument across every product, as the exposure hedge counts it.

        Args:
            instrument: The tradingmachine.assets.instruments.TradeableInstrument to read.

        Returns:
            The int net quantity, positive when long and negative when short.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the positions.
        """
        positions = instrument.net_positions
        if positions is None:
            return 0
        total = 0
        for row in positions.to_dict("records"):
            total = total + int(row["quantity"])
        return total

    def run(self) -> None:
        """Previews the hedge, starts it, prints it and cancels it.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for a share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        preview = self.build_order(dry_run=True).place()
        print("A dry run, which sends and records nothing, says UBI would send:")
        print(preview.get("request", preview))
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
    WeightedExposureHedge().run()
