"""Show how basket members are described when a basket is stored.

The program builds one weighted member for a share, one for an exchange traded fund and one for an index, prints each member as it appears in Python and then the fields `document` gives it for MongoDB, which name the instrument by its UBI id beside its readable identity.

Typical usage example:

  .venv/bin/python examples/asset_baskets/basket_member/basket_member/member_documents.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.assets import equities
from tradingmachine.assets import funds


class MemberDocuments:
    """A printout of a few members and their stored form.

    Attributes:
        members: The list of tradingmachine.asset_baskets.basket_member.BasketMember printed.
    """

    def __init__(self):
        """Looks the three instruments up in UBI and makes a weighted member of each.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the instruments.
        """
        infosys = equities.Equity(exchange="nse", symbol="INFY")
        gold_fund = funds.ExchangeTradedFund(exchange="nse", symbol="GOLDBEES")
        nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.members = [
            basket_member.BasketMember(infosys, weight=0.5),
            basket_member.BasketMember(gold_fund, weight=0.3),
            basket_member.BasketMember(nifty, weight=0.2),
        ]

    def run(self) -> None:
        """Prints each member and its stored fields.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for member in self.members:
            print(member)
            document = member.document()
            for field in [
                "instrument_id",
                "segment",
                "symbol",
                "weight",
            ]:
                print(f"  {field:<14} {document[field]}")


if __name__ == "__main__":
    MemberDocuments().run()
