"""Store an exchange traded fund's holdings linked to the fund and find them again through it.

The program stores the holdings of the GOLDBEES fund under the temporary name `example-etf-goldbees`, linked to the fund, then finds them again with `BasketStore.load_for_instrument` as `ExchangeTradedFund.constituents` does, prints what came back and the stored form's link fields, and deletes the stored copy before it ends, whatever happens. A gold fund holds gold, which UBI has no cash price for, so the basket stands in with the gold fund itself at a weight of 97% and 3% left unpriced as cash.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exchange_traded_fund_constituents/exchange_traded_fund_constituents/stored_fund_holdings.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import basket_store
from tradingmachine.asset_baskets import exchange_traded_fund_constituents
from tradingmachine.assets import funds

NAME = "example-etf-goldbees"

EFFECTIVE_DATE = "2026-09-01"


class StoredFundHoldings:
    """A fund's holdings stored with a link to the fund.

    Attributes:
        store: The tradingmachine.asset_baskets.basket_store.BasketStore the holdings are saved in.
        fund: The tradingmachine.assets.funds.ExchangeTradedFund the holdings belong to.
    """

    def __init__(self):
        """Creates the store and looks the fund up in UBI.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the fund.
        """
        self.store = basket_store.BasketStore()
        self.fund = funds.ExchangeTradedFund(exchange="nse", symbol="GOLDBEES")

    def build_holdings(
        self,
    ) -> exchange_traded_fund_constituents.ExchangeTradedFundConstituents:
        """Builds the holdings basket linked to the fund.

        Returns:
            The tradingmachine.asset_baskets.exchange_traded_fund_constituents.ExchangeTradedFundConstituents to store.

        Raises:
            Nothing.
        """
        members = [
            basket_member.BasketMember(self.fund, weight=97),
        ]
        return exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
            name=NAME,
            members=members,
            fund=self.fund,
            unmapped_weight=0.03,
        )

    def run(self) -> None:
        """Saves the holdings, finds them through the fund, prints them, and deletes them.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        holdings = self.build_holdings()
        document = self.store.save(
            holdings, effective_date=EFFECTIVE_DATE, source="example"
        )
        try:
            print(
                f"Stored {document['name']} linked to {document['linked_instrument_id']}"
            )
            print(
                f"Indicative value stored: {document['indicative_net_asset_value_instrument_id']}"
            )
            found = self.store.load_for_instrument(self.fund)
            print(f"Found through the fund: {found}")
            print(
                f"Its fund: {found.fund.symbol}, unmapped weight {found.unmapped_weight}"
            )
        finally:
            self.store.delete(NAME, EFFECTIVE_DATE)


if __name__ == "__main__":
    StoredFundHoldings().run()
