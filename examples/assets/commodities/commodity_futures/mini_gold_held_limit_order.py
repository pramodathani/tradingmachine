"""Bid for one lot of mini gold well below the market, then cancel the bid.

The program bids for one lot of the soonest GOLDM future three per cent below its last price. A commodity quantity is counted in quotation units and must be a whole number of lots, so the program sends the contract's lot size as the quantity. UBI's order engine holds a plain day limit order until the offer comes down to its price, so the program reads back the parent it holds and cancels it at once.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_futures/mini_gold_held_limit_order.py
"""

from tradingmachine.assets import commodities


class MiniGoldHeldLimitOrder:
    """One far-away bid for a commodity future, held by the order engine and then cancelled.

    Attributes:
        contract: The tradingmachine.assets.commodities.CommodityFutures the bid is for.
        discount: The float fraction below the last price at which to bid.
    """

    def __init__(self, underlying_symbol: str = "GOLDM", discount: float = 0.03):
        """Builds the contract with the soonest expiry.

        Args:
            underlying_symbol: The str mcx symbol of the commodity, such as `GOLDM`.
            discount: The float fraction below the last price at which to bid.

        Raises:
            ValueError: No futures are listed on the commodity.
            tradingmachine.assets.exceptions.CommodityFuturesError: UBI has no such contract.
        """
        expiries = commodities.CommodityFutures.expiries(
            exchange="mcx",
            underlying_symbol=underlying_symbol,
        )
        if not expiries:
            raise ValueError(f"No futures are listed on {underlying_symbol}")
        self.contract = commodities.CommodityFutures(
            exchange="mcx",
            underlying_symbol=underlying_symbol,
            expiry_date=expiries[0],
        )
        self.discount = discount

    def bid_price(self) -> float:
        """Works out the bid price, rounded down to the contract's tick size.

        Returns:
            The float price in rupees.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.ServiceUnavailableError: UBI has no quote for the contract.
        """
        tick_size = float(self.contract.tick_size)
        target = self.contract.last_price * (1 - self.discount)
        ticks = int(target / tick_size)
        return round(ticks * tick_size, 4)

    def run(self) -> None:
        """Places the bid for one lot, prints the engine's answer and cancels it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        contract = self.contract
        price = self.bid_price()
        print(f"{contract.underlying_symbol} {contract.expiry_date}")
        print(f"Last price {contract.last_price}, bidding {price}")
        print(f"Quantity: one lot of {contract.lot_size} units")
        answer = contract.buy_at_limit_price(
            price=price,
            quantity=contract.lot_size,
            product="nrml",
            tag="examplegoldbid",
        )
        parent_id = answer.get("parent_id")
        try:
            print(f"Outcome: {answer['outcome']}, parent id: {parent_id}")
            if parent_id is not None:
                parent = contract.parent(parent_id)
                print(f"The engine holds it in state {parent['state']}")
        finally:
            if parent_id is not None:
                cancelled = contract.cancel_parent(parent_id)
                print(f"After cancelling: {cancelled['state']}")


if __name__ == "__main__":
    MiniGoldHeldLimitOrder().run()
