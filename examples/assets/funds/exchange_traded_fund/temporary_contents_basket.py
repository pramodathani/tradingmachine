"""Link a temporary contents basket to NIFTYBEES, measure it, and remove it.

UBI stores no fund holdings, so a fund's `constituents` are whatever basket was saved in MongoDB with the fund as its linked instrument. The program saves a five-share basket weighted roughly like the top of the NIFTY, reads it back through the fund, prints its weights, live prices and day change next to the fund's own, and deletes the basket again, whatever happens in between.

Typical usage example:

  .venv/bin/python examples/assets/funds/exchange_traded_fund/temporary_contents_basket.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import basket_store
from tradingmachine.asset_baskets import exchange_traded_fund_constituents
from tradingmachine.assets import equities
from tradingmachine.assets import funds

BASKET_NAME = "EXAMPLE_NIFTYBEES_TOP_FIVE"


class TemporaryContentsBasket:
    """A short-lived contents basket for one exchange traded fund.

    Attributes:
        fund: The funds.ExchangeTradedFund the basket is linked to.
        store: The basket_store.BasketStore the basket is saved in.
        weights: The dict mapping each str nse symbol to its float weight.
    """

    def __init__(self):
        """Looks NIFTYBEES up and opens the basket store.

        Raises:
            tradingmachine.assets.exceptions.ExchangeTradedFundError: UBI has no such fund.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        self.fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
        self.store = basket_store.BasketStore()
        self.weights = {
            "HDFCBANK": 0.30,
            "RELIANCE": 0.25,
            "ICICIBANK": 0.20,
            "INFY": 0.15,
            "BHARTIARTL": 0.10,
        }

    def run(self) -> None:
        """Saves the basket, reports on it through the fund, and deletes it.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        saved = self.store.save(self._build_basket(), source="example")
        print(f"Saved {BASKET_NAME} for {saved['effective_date']}")
        try:
            self._report()
        finally:
            deleted = self.store.delete(BASKET_NAME, saved["effective_date"])
            print(f"Deleted the basket again: {deleted}")

    def _build_basket(
        self,
    ) -> exchange_traded_fund_constituents.ExchangeTradedFundConstituents:
        """Builds the basket of the five shares, linked to the fund.

        Returns:
            The exchange_traded_fund_constituents.ExchangeTradedFundConstituents basket.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        members = []
        for symbol, weight in self.weights.items():
            share = equities.Equity(exchange="nse", symbol=symbol)
            members.append(basket_member.BasketMember(instrument=share, weight=weight))
        return exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
            name=BASKET_NAME,
            members=members,
            fund=self.fund,
        )

    def _report(self) -> None:
        """Reads the basket back through the fund and prints what it holds and how it moved.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        contents = self.fund.constituents
        if contents is None:
            print("The fund found no basket, so nothing was linked.")
            return
        print(repr(contents))
        print(contents.weights)
        print(contents.last_prices)
        print(f"Basket day change: {contents.day_change_percent} per cent")
        quote = self.fund.ohlc
        fund_change = (quote["last_price"] / quote["previous_close"] - 1) * 100
        print(f"NIFTYBEES day change: {fund_change:.2f} per cent")


if __name__ == "__main__":
    TemporaryContentsBasket().run()
