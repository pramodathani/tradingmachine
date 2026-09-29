"""Bid for one lot of a Nifty call far below its offer, then cancel the bid.

The program picks the Nifty call about two per cent out of the money on the soonest expiry after today, bids for one lot at half its best offer, and cancels the bid at once. UBI's order engine holds a plain day limit order until the offer comes down to its price, so the bid never reaches the exchange.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_index_option/nifty_option_held_limit_order.py
"""

import datetime

from tradingmachine.assets import equities


class NiftyOptionHeldLimitOrder:
    """One far-away bid for a Nifty call, held by the order engine and then cancelled.

    Attributes:
        option: The tradingmachine.assets.equities.EquityIndexOption the bid is for.
    """

    def __init__(self):
        """Chooses the call and looks it up in UBI.

        Raises:
            ValueError: No options are listed on the Nifty.
            tradingmachine.assets.exceptions.EquityIndexOptionError: UBI has no such option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        if not expiries:
            raise ValueError("No options are listed on the Nifty")
        expiry_date = expiries[0]
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                expiry_date = expiry
                break
        target = index.last_price * 1.02
        strikes = equities.EquityIndexOption.strikes(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiry_date,
        )
        strike_price = strikes[0]
        for strike in strikes:
            if abs(strike - target) < abs(strike_price - target):
                strike_price = strike
        self.option = equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiry_date,
            strike_price=strike_price,
            option_type="CE",
            underlying=index,
        )

    def bid_price(self) -> float:
        """Works out a bid at half the best offer, or half the last price, rounded to the tick.

        Returns:
            The float price in rupees, never below one tick.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.ServiceUnavailableError: UBI has no quote for the option.
        """
        offer = self.option.best_offer
        if offer is None:
            reference = self.option.last_price
        else:
            reference = offer["price"]
        tick_size = float(self.option.tick_size)
        ticks = int(reference * 0.5 / tick_size)
        if ticks < 1:
            ticks = 1
        return round(ticks * tick_size, 2)

    def run(self) -> None:
        """Places the bid for one lot, prints the engine's answer and cancels it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        price = self.bid_price()
        print(
            f"NIFTY {self.option.strike_price} CE expiring "
            f"{self.option.expiry_date}: last {self.option.last_price}"
        )
        print(f"Bidding {price} for one lot of {self.option.lot_size}")
        answer = self.option.buy_at_limit_price(
            price=price,
            quantity=self.option.lot_size,
            product="nrml",
            tag="exampleoptionbid",
        )
        parent_id = answer.get("parent_id")
        try:
            print(f"Outcome: {answer['outcome']}, parent id: {parent_id}")
        finally:
            if parent_id is not None:
                cancelled = self.option.cancel_parent(parent_id)
                print(f"After cancelling: {cancelled['state']}")


if __name__ == "__main__":
    NiftyOptionHeldLimitOrder().run()
